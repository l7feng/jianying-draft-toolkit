"""Chinese AAF export window; independent of host string-widget support."""
from __future__ import annotations
import argparse,json,os,pathlib,subprocess,sys,time,uuid
import tkinter as tk
from tkinter import ttk,filedialog,messagebox

BASE=pathlib.Path(os.environ.get('LOCALAPPDATA',str(pathlib.Path.home())))/'JYMixBridge'
DEFAULT_OUTPUT='D:/Out'
LEGACY_OUTPUT='D:/My-Temporary/Backup-Jianying/Tools/out'

def clean_path(text):
    return text.strip().strip('"').strip()

def validate_paths(source,output):
    source=clean_path(source);output=clean_path(output)
    if not source:raise ValueError('请先选择一集剪映草稿。')
    if not output:raise ValueError('请选择AAF输出文件夹。')
    s=pathlib.Path(source);o=pathlib.Path(output)
    if not s.is_absolute() or not o.is_absolute():raise ValueError('请使用完整路径，例如D:\\Out。')
    s=s.resolve();o=o.resolve()
    if not s.is_dir():raise ValueError('草稿目录不存在，请重新选择。')
    if not ((s/'draft_content.json').is_file() or (s/'Timelines').is_dir()):
        raise ValueError('请选择具体一集的草稿文件夹，不要选择整个草稿库或视频素材目录。')
    if o==s or s in o.parents:raise ValueError('输出文件夹必须位于草稿目录之外。')
    if o.exists() and not o.is_dir():raise ValueError('输出路径是文件，请选择文件夹。')
    return s,o

def read_preferences():
    try:
        data=json.loads((BASE/'panel-preferences.json').read_text(encoding='utf-8'))
        return data if isinstance(data,dict) and all(isinstance(data.get(k,''),str) for k in ['source','output']) else {}
    except (OSError,ValueError):return {}

class ExportWindow:
    def __init__(self,root,source='',output=''):
        self.root=root;self.process=None;self.job=None;self.result_path=None;self.last_log=''
        root.title('剪映混音交互 · AAF导出 0.2');root.geometry('760x420');root.minsize(640,390)
        root.configure(bg='#f5f5f3')
        style=ttk.Style(root);style.configure('.',font=('Microsoft YaHei UI',10))
        style.configure('Title.TLabel',font=('Microsoft YaHei UI',19,'bold'))
        style.configure('Hint.TLabel',foreground='#666666')
        frame=ttk.Frame(root,padding=24);frame.pack(fill='both',expand=True);frame.columnconfigure(0,weight=1)
        ttk.Label(frame,text='导出音频 AAF',style='Title.TLabel').grid(row=0,column=0,sticky='w')
        ttk.Label(frame,text='先保存剪映工程，再选择一集草稿。',style='Hint.TLabel').grid(row=1,column=0,sticky='w',pady=(4,20))
        prefs=read_preferences()
        if not output or output.replace('\\','/').rstrip('/').lower()==LEGACY_OUTPUT.lower():output=prefs.get('output',DEFAULT_OUTPUT)
        self.source=tk.StringVar(root,value=source or prefs.get('source',''))
        self.output=tk.StringVar(root,value=output or DEFAULT_OUTPUT)
        self.controls=[]
        self.path_row(frame,2,'单集草稿',self.source,True)
        self.path_row(frame,4,'输出文件夹',self.output,False)
        actions=ttk.Frame(frame);actions.grid(row=6,column=0,sticky='ew',pady=(22,12))
        self.start_button=ttk.Button(actions,text='开始导出AAF',command=self.start);self.start_button.pack(side='left')
        self.open_button=ttk.Button(actions,text='打开输出文件夹',command=self.open_output);self.open_button.pack(side='left',padx=10)
        ttk.Button(actions,text='任务详情',command=self.show_details).pack(side='right')
        self.status=tk.StringVar(root,value='就绪 · 48千赫兹 / 24位 / 内嵌音频')
        ttk.Label(frame,textvariable=self.status,wraplength=650).grid(row=7,column=0,sticky='w')
        self.progress=ttk.Progressbar(frame,mode='indeterminate');self.progress.grid(row=8,column=0,sticky='ew',pady=(10,12))
        ttk.Label(frame,text='保留剪辑位置，烘焙固定音量和线性淡化；剪映专有效果不包含在内。',style='Hint.TLabel',wraplength=650).grid(row=9,column=0,sticky='w')
        root.protocol('WM_DELETE_WINDOW',self.close)

    def path_row(self,frame,row,label,variable,is_source):
        ttk.Label(frame,text=label).grid(row=row,column=0,sticky='w',pady=(7,5))
        line=ttk.Frame(frame);line.grid(row=row+1,column=0,sticky='ew');line.columnconfigure(0,weight=1)
        entry=ttk.Entry(line,textvariable=variable);entry.grid(row=0,column=0,sticky='ew',ipady=4)
        button=ttk.Button(line,text='选择文件夹…',command=lambda:self.browse(variable,is_source));button.grid(row=0,column=1,padx=(10,0))
        self.controls.extend([entry,button])

    def browse(self,variable,is_source):
        current=pathlib.Path(clean_path(variable.get()) or 'D:/')
        selected=filedialog.askdirectory(parent=self.root,title='选择一集剪映草稿' if is_source else '选择AAF输出文件夹',initialdir=str(current if current.is_dir() else current.parent),mustexist=is_source)
        if selected:variable.set(selected)

    def start(self):
        if self.process and self.process.poll() is None:return
        try:
            source,output=validate_paths(self.source.get(),self.output.get())
            BASE.mkdir(parents=True,exist_ok=True)
            job_id=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]
            self.job=BASE/job_id;self.result_path=None;self.last_log=''
            worker=pathlib.Path(__file__).with_name('aaf_worker.py')
            self.process=subprocess.Popen([sys.executable,str(worker),'--source',str(source),'--output',str(output),'--job-id',job_id],creationflags=0x08000000 if os.name=='nt' else 0)
            self.source.set(str(source));self.output.set(str(output))
            try:
                temp=BASE/('panel-preferences-'+uuid.uuid4().hex+'.tmp')
                temp.write_text(json.dumps({'source':str(source),'output':str(output)},ensure_ascii=False),encoding='utf-8');os.replace(temp,BASE/'panel-preferences.json')
            except OSError:pass
        except (ValueError,OSError) as exc:
            self.status.set(str(exc));messagebox.showerror('无法开始导出',str(exc),parent=self.root);return
        self.start_button.configure(state='disabled')
        for control in self.controls:control.configure(state='disabled')
        self.status.set('正在读取草稿…');self.progress.start(15);self.root.after(300,self.poll)

    def poll(self):
        try:
            self.last_log=(self.job/'任务日志.txt').read_text(encoding='utf-8',errors='replace')
            lines=[x for x in self.last_log.splitlines() if x.strip()]
            if lines:self.status.set(lines[-1][-180:])
        except OSError:pass
        if self.process.poll() is None:self.root.after(300,self.poll);return
        self.progress.stop();self.start_button.configure(state='normal')
        for control in self.controls:control.configure(state='normal')
        try:
            result=json.loads((self.job/'result.json').read_text(encoding='utf-8'))
            if not result.get('ok'):raise ValueError(result.get('error','导出失败，请查看任务详情。'))
            self.result_path=pathlib.Path(result['result']['aaf'])
            if not self.result_path.is_file():raise ValueError('任务报告成功，但AAF文件不存在。')
            self.status.set(f'导出完成 · {result["result"]["tracks"]}轨 · {self.result_path.name}')
            warnings=result['result'].get('warnings',[])
            if warnings:self.status.set(self.status.get()+' · 有交接提示，请查看输出文件夹内的交接说明')
        except (OSError,ValueError,KeyError) as exc:
            self.status.set('导出失败：'+str(exc));messagebox.showerror('AAF导出失败',str(exc),parent=self.root)

    def open_output(self):
        if not self.result_path and not clean_path(self.output.get()):
            messagebox.showinfo('输出文件夹','请先选择输出文件夹。',parent=self.root);return
        path=self.result_path.parent if self.result_path else pathlib.Path(clean_path(self.output.get()))
        if path.is_dir():os.startfile(str(path))
        else:messagebox.showinfo('输出文件夹','文件夹尚未创建，成功导出后可打开。',parent=self.root)

    def show_details(self):
        if self.job and self.job.is_dir():os.startfile(str(self.job))
        else:messagebox.showinfo('任务详情','开始导出后，这里可以查看本次任务日志和结果。',parent=self.root)

    def close(self):
        if self.process and self.process.poll() is None:
            if not messagebox.askyesno('任务仍在执行','关闭窗口后，后台会继续导出。确定关闭？',parent=self.root):return
        self.root.destroy()

def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument('--source',default='');parser.add_argument('--output',default='');args=parser.parse_args(argv)
    root=tk.Tk();ExportWindow(root,args.source,args.output);root.mainloop()

if __name__=='__main__':main()
