/* JY Mix Bridge OFX, project 72. OpenFX headers: BSD-3-Clause.
 * Explicit buttons dispatch an external worker; render only copies pixels. */
#include <windows.h>
#define CP_UTF8 65001
#define MB_ERR_INVALID_CHARS 8
__declspec(dllimport) int WINAPI MultiByteToWideChar(UINT,DWORD,LPCSTR,int,LPWSTR,int);
__declspec(dllimport) HINSTANCE WINAPI ShellExecuteW(HWND,LPCWSTR,LPCWSTR,LPCWSTR,LPCWSTR,INT);
#define DEFAULT_OUTPUT "D:/Out"
#define WORKER_PATH "\104\072\134\101\151\055\106\151\154\145\163\134\122\145\160\157\163\134\107\151\164\110\165\142\134\060\062\055\152\151\141\156\171\151\156\147\055\144\162\141\146\164\055\164\157\157\154\153\151\164\134\163\162\143\134\152\151\141\156\171\151\156\147\055\155\151\170\055\157\146\170\134\141\141\146\137\167\157\162\153\145\162\056\160\171"
#define PYTHON_EXE "\104\072\057\101\151\055\106\151\154\145\163\057\124\157\157\154\163\057\102\165\151\154\144\105\156\166\057\160\171\063\061\062\057\160\171\164\150\157\156\167\056\145\170\145"

#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <stdlib.h>
#include "ofxImageEffect.h"
#include "ofxProperty.h"
/* Three real OFX modules, shared implementation; default retains legacy build. */
#ifndef JY_PLUGIN_MODE
#define JY_PLUGIN_MODE -1
#endif
#if JY_PLUGIN_MODE == 0
#define JY_PLUGIN_ID "local.jytools.AAFExport"
#define JY_PLUGIN_LABEL "剪映AAF导出 v0.8"
#define JY_MEMORY_NAME L"\\native-paths-aaf.ini"
#elif JY_PLUGIN_MODE == 2
#define JY_PLUGIN_ID "local.jytools.TrackExport"
#define JY_PLUGIN_LABEL "剪映单集分轨 v0.8"
#define JY_MEMORY_NAME L"\\native-paths-tracks.ini"
#elif JY_PLUGIN_MODE == 3
#define JY_PLUGIN_ID "local.jytools.BatchTrackExport"
#define JY_PLUGIN_LABEL "剪映多集分轨 v0.8"
#define JY_MEMORY_NAME L"\\native-paths-batch.ini"
#else
#define JY_PLUGIN_ID "local.jytools.MixBridge"
#define JY_PLUGIN_LABEL "剪映混音交互 v0.7"
#define JY_MEMORY_NAME L"\\native-paths.ini"
#endif
#if JY_PLUGIN_MODE >= 0
#define JY_VERSION_MINOR 8
#define JY_VERSION_LABEL "0.8"
#else
#define JY_VERSION_MINOR 7
#define JY_VERSION_LABEL "0.7"
#endif
static OfxHost *gHost;
static OfxPropertySuiteV1 *P;
static OfxImageEffectSuiteV1 *E;
static OfxParameterSuiteV1 *Q;
static LONG renderLogs;
static HANDLE activeWorker;
static char activeJobID[64];
typedef struct Session {OfxImageEffectHandle effect;char *values[6];int syncing;struct Session *next;} Session;
static Session *sessions;
static const char *ownedKeys[]={"source_path","output_path","last_job","source_origin","task_status","batch_source_path"};
static Session *sessionFor(OfxImageEffectHandle effect){Session *s=sessions;while(s&&s->effect!=effect)s=s->next;if(!s){s=(Session*)calloc(1,sizeof(Session));if(s){s->effect=effect;s->next=sessions;sessions=s;}}return s;}
static void rememberValue(OfxImageEffectHandle effect,const char *key,const char *value){Session *s=sessionFor(effect);int i;if(!s)return;for(i=0;i<6;i++)if(!strcmp(key,ownedKeys[i])){char *copy=(char*)malloc(strlen(value)+1);if(copy){strcpy(copy,value);free(s->values[i]);s->values[i]=copy;}break;}}
static void forgetSession(OfxImageEffectHandle effect){Session **slot=&sessions,*s;int i;while(*slot&&(*slot)->effect!=effect)slot=&(*slot)->next;if(!*slot)return;s=*slot;*slot=s->next;for(i=0;i<6;i++)free(s->values[i]);free(s);}
static void reconcileSession(OfxImageEffectHandle);
static void projectSummary(OfxImageEffectHandle);
static void openResult(OfxImageEffectHandle);

static int readMemory(const char *,char *,int);
static OfxStatus restoreMemory(OfxImageEffectHandle,int);
static OfxStatus setString(OfxImageEffectHandle,const char *,const char *);
static void existingInitial(const char *,const char *,char *,int);
static void logline(const char *fmt, ...) {
  char dir[MAX_PATH], path[MAX_PATH]; FILE *f; va_list ap; SYSTEMTIME st;
  if (!GetEnvironmentVariableA("LOCALAPPDATA", dir, MAX_PATH-24)) return;
  strcat(dir, "\\JYMixBridge"); CreateDirectoryA(dir, NULL);
  snprintf(path, sizeof(path), "%s\\host-%lu.log", dir, (unsigned long)GetCurrentProcessId());
  f=fopen(path,"a"); if(!f)return; GetLocalTime(&st);
  fprintf(f,"%04d-%02d-%02d %02d:%02d:%02d ",st.wYear,st.wMonth,st.wDay,st.wHour,st.wMinute,st.wSecond);
  va_start(ap,fmt); vfprintf(f,fmt,ap); va_end(ap); fputc('\n',f); fclose(f);
}
static void dumpProps(OfxPropertySetHandle ps,const char *where) {
  const char *names[]={kOfxPropName,kOfxPropLabel,kOfxPropVersionLabel,
    kOfxImageEffectPropSupportedContexts,kOfxImageEffectPropSupportedPixelDepths,
    kOfxImageEffectPropContext,NULL};
  int k,i,n; char *v;
  if(!ps||!P)return;
  for(k=0;names[k];k++) if(P->propGetDimension(ps,names[k],&n)==kOfxStatOK)
    for(i=0;i<n&&i<32;i++) if(P->propGetString(ps,names[k],i,&v)==kOfxStatOK&&v)
      logline("%s %s[%d]=%.200s",where,names[k],i,v);
}
static void setHost(OfxHost *h) { gHost=h; }
static OfxStatus load(void) {
  const char *suites[]={kOfxPropertySuite,kOfxImageEffectSuite,kOfxParameterSuite,
    kOfxMemorySuite,kOfxMultiThreadSuite,kOfxMessageSuite,"OfxProgressSuite",
    "OfxInteractSuite","OfxImageEffectOpenGLRenderSuite",NULL};
  int i;
  if(!gHost||!gHost->fetchSuite)return kOfxStatErrMissingHostFeature;
  logline("plugin %s load",JY_PLUGIN_LABEL);
  for(i=0;suites[i];i++)logline("suite %s v1=%s",suites[i],gHost->fetchSuite(gHost->host,suites[i],1)?"available":"missing");
  P=(OfxPropertySuiteV1*)gHost->fetchSuite(gHost->host,kOfxPropertySuite,1);
  E=(OfxImageEffectSuiteV1*)gHost->fetchSuite(gHost->host,kOfxImageEffectSuite,1);
  Q=(OfxParameterSuiteV1*)gHost->fetchSuite(gHost->host,kOfxParameterSuite,1);
  if(!P||!E||!Q)return kOfxStatErrMissingHostFeature;
  dumpProps(gHost->host,"host");
  {const char *flags[]={kOfxParamHostPropSupportsCustomInteract,kOfxParamHostPropMaxPages,NULL};int j,value;
   for(j=0;flags[j];j++){OfxStatus result=P->propGetInt(gHost->host,flags[j],0,&value);logline("layout capability %s status=%d value=%d",flags[j],result,result?0:value);}}
  return kOfxStatOK;
}
static OfxStatus describe(OfxImageEffectHandle effect) {
  OfxPropertySetHandle ps=NULL;
  if(E->getPropertySet(effect,&ps)!=kOfxStatOK)return kOfxStatErrBadHandle;
  P->propSetString(ps,kOfxPropLabel,0,JY_PLUGIN_LABEL);
  P->propSetString(ps,kOfxPropShortLabel,0,JY_PLUGIN_LABEL);
  P->propSetString(ps,kOfxPropLongLabel,0,JY_PLUGIN_LABEL);
  P->propSetString(ps,kOfxPropVersionLabel,0,JY_VERSION_LABEL);
  P->propSetString(ps,kOfxImageEffectPluginPropGrouping,0,"剪映混音");
  P->propSetString(ps,kOfxImageEffectPropSupportedContexts,0,kOfxImageEffectContextFilter);
  P->propSetString(ps,kOfxImageEffectPropSupportedContexts,1,kOfxImageEffectContextGeneral);
  P->propSetString(ps,kOfxImageEffectPropSupportedPixelDepths,0,kOfxBitDepthByte);
  P->propSetString(ps,kOfxImageEffectPropSupportedPixelDepths,1,kOfxBitDepthShort);
  P->propSetString(ps,kOfxImageEffectPropSupportedPixelDepths,2,kOfxBitDepthFloat);
  P->propSetInt(ps,kOfxImageEffectPropSupportsTiles,0,0);
  P->propSetInt(ps,kOfxImageEffectPropSupportsMultiResolution,0,0);
  P->propSetInt(ps,kOfxImageEffectPropTemporalClipAccess,0,0);
  P->propSetString(ps,kOfxImageEffectPluginRenderThreadSafety,0,kOfxImageEffectRenderInstanceSafe);
  return kOfxStatOK;
}
static OfxStatus strparam(OfxParamSetHandle set,const char *key,const char *label,const char *value,const char *mode){
  OfxPropertySetHandle ps;OfxStatus s=Q->paramDefine(set,kOfxParamTypeString,key,&ps);if(s)return s;
  P->propSetString(ps,kOfxPropLabel,0,label);P->propSetString(ps,kOfxParamPropDefault,0,value);
  P->propSetString(ps,kOfxParamPropStringMode,0,kOfxParamStringIsLabel);
  P->propSetInt(ps,kOfxParamPropPluginMayWrite,0,1);

  P->propSetInt(ps,kOfxParamPropAnimates,0,0);
  P->propSetInt(ps,kOfxParamPropPersistant,0,1);
  P->propSetInt(ps,kOfxParamPropEnabled,0,1);
  /* Paths are selected by native buttons and retained in project parameters. */
  P->propSetInt(ps,kOfxParamPropSecret,0,0);
  return kOfxStatOK;
}
static OfxStatus groupParam(OfxParamSetHandle set,const char *key,const char *label){
  OfxPropertySetHandle ps;OfxStatus status=Q->paramDefine(set,kOfxParamTypeGroup,key,&ps);
  if(status){logline("host rejected parameter group %s status=%d; using ordered flat layout",key,status);return status;}
  P->propSetString(ps,kOfxPropLabel,0,label);P->propSetInt(ps,kOfxParamPropGroupOpen,0,1);return kOfxStatOK;
}
static void parentParam(OfxParamSetHandle set,const char *key,const char *parent){
  OfxParamHandle handle;OfxPropertySetHandle ps;
  if(!Q->paramGetHandle(set,key,&handle,&ps))P->propSetString(ps,kOfxParamPropParent,0,parent);
}
static OfxStatus buttonParam(OfxParamSetHandle set,const char *key,const char *label,const char *parent){
  OfxPropertySetHandle ps;OfxStatus status=Q->paramDefine(set,kOfxParamTypePushButton,key,&ps);if(status)return status;
  P->propSetString(ps,kOfxPropLabel,0,label);if(parent)P->propSetString(ps,kOfxParamPropParent,0,parent);return kOfxStatOK;
}
static OfxStatus context(OfxImageEffectHandle effect,OfxPropertySetHandle in){
  OfxParamSetHandle set;OfxPropertySetHandle ps;OfxParamHandle handle;int i,g1,g2,g3;OfxStatus status;
  char recentSource[32768]={0},recentOutput[32768]={0};const char *clips[]={"Source","Output"};
  const char *executionKeys[]={"inspect_project","open_report","export_aaf","refresh_status","open_jobs","open_output"};
  const char *executionLabels[]={"检查工程","查看检查报告","检查并导出AAF","刷新任务状态","查看本次任务","打开输出目录"};
  for(i=0;i<2;i++){if((status=E->clipDefine(effect,clips[i],&ps)))return status;
    P->propSetString(ps,kOfxImageEffectPropSupportedComponents,0,kOfxImageComponentRGBA);P->propSetInt(ps,kOfxImageEffectPropSupportsTiles,0,0);}
  if((status=E->getParamSet(effect,&set)))return status;
  g1=groupParam(set,"group_project","工程与路径")==kOfxStatOK;
  readMemory("source_path",recentSource,sizeof(recentSource));readMemory("output_path",recentOutput,sizeof(recentOutput));
  if((status=strparam(set,"source_path","单集草稿",recentSource,kOfxParamStringIsSingleLine)))return status;
  if(g1)parentParam(set,"source_path","group_project");
  if((status=buttonParam(set,"choose_source","选择草稿目录",g1?"group_project":NULL)))return status;
  if((status=strparam(set,"output_path","输出目录",recentOutput[0]?recentOutput:DEFAULT_OUTPUT,kOfxParamStringIsSingleLine)))return status;
  if(g1)parentParam(set,"output_path","group_project");
  if((status=buttonParam(set,"choose_output","选择输出目录",g1?"group_project":NULL)))return status;
  if((status=buttonParam(set,"restore_paths","读取上次目录",g1?"group_project":NULL)))return status;
  if((status=strparam(set,"source_origin","工程来源","手选或记忆目录；尚未自动识别当前工程",NULL)))return status;
  if(g1)parentParam(set,"source_origin","group_project");
  {char recent[32768]={0};readMemory("batch_source_path",recent,sizeof(recent));
   if((status=strparam(set,"batch_source_path","多集草稿父目录",recent,NULL)))return status;
   if(g1)parentParam(set,"batch_source_path","group_project");
   if((status=buttonParam(set,"choose_batch_source","选择多集目录",g1?"group_project":NULL)))return status;}
  g2=groupParam(set,"group_export","导出设置")==kOfxStatOK;
  if((status=strparam(set,"export_format","交付格式","AAF / 分轨WAV · 48千赫兹 / 24位",NULL)))return status;
  if(g2)parentParam(set,"export_format","group_export");
  if((status=Q->paramDefine(set,kOfxParamTypeChoice,"handles_mode",&ps)))return status;
  P->propSetString(ps,kOfxPropLabel,0,"AAF片段前后余量");P->propSetInt(ps,kOfxParamPropDefault,0,0);
  P->propSetInt(ps,kOfxParamPropAnimates,0,0);P->propSetInt(ps,kOfxParamPropPersistant,0,1);
  P->propSetString(ps,kOfxParamPropChoiceOption,0,"不保留");P->propSetString(ps,kOfxParamPropChoiceOption,1,"前后各2秒");P->propSetString(ps,kOfxParamPropChoiceOption,2,"前后各5秒");
  if(g2)P->propSetString(ps,kOfxParamPropParent,0,"group_export");
  if((status=strparam(set,"handoff_mode","声音处理","固定音量和线性淡化；其他效果见检查报告",NULL)))return status;
  if(g2)parentParam(set,"handoff_mode","group_export");
  g3=groupParam(set,"group_execute","检查与执行")==kOfxStatOK;
  if((status=strparam(set,"task_status","任务状态","就绪：导出时自动检查工程",NULL)))return status;
  if(g3)parentParam(set,"task_status","group_execute");
  for(i=0;i<6;i++)if((status=buttonParam(set,executionKeys[i],executionLabels[i],g3?"group_execute":NULL)))return status;
  if((status=buttonParam(set,"export_stems","导出本集所有音频轨",g3?"group_execute":NULL)))return status;
  if((status=buttonParam(set,"export_batch_stems","批量导出多集音频轨",g3?"group_execute":NULL)))return status;
  if((status=buttonParam(set,"toggle_details","展开／收起任务详情",g3?"group_execute":NULL)))return status;
  {const char *hidden[]={"task_status","refresh_status","open_report","open_jobs","restore_paths","handoff_mode",NULL};int j;
   for(j=0;hidden[j];j++)if(!Q->paramGetHandle(set,hidden[j],&handle,&ps))P->propSetInt(ps,kOfxParamPropSecret,0,1);}
  if((status=strparam(set,"last_job","本次任务标识","",NULL)))return status;
  Q->paramGetHandle(set,"last_job",&handle,&ps);P->propSetInt(ps,kOfxParamPropSecret,0,1);
  if((status=buttonParam(set,"fill_output","旧默认目录入口",NULL)))return status;
  Q->paramGetHandle(set,"fill_output",&handle,&ps);P->propSetInt(ps,kOfxParamPropSecret,0,1);
  if((status=buttonParam(set,"open_panel","旧窗口入口（已停用）",NULL)))return status;
  Q->paramGetHandle(set,"open_panel",&handle,&ps);P->propSetInt(ps,kOfxParamPropSecret,0,1);
#if JY_PLUGIN_MODE >= 0
  {const char *hide[]={
#if JY_PLUGIN_MODE == 0
    "batch_source_path","choose_batch_source","export_stems","export_batch_stems",
#elif JY_PLUGIN_MODE == 2
    "batch_source_path","choose_batch_source","export_aaf","export_batch_stems","handles_mode",
#elif JY_PLUGIN_MODE == 3
    "source_path","choose_source","source_origin","inspect_project","export_aaf","export_stems","handles_mode","open_report",
#endif
    NULL};int j;for(j=0;hide[j];j++)if(!Q->paramGetHandle(set,hide[j],&handle,&ps))P->propSetInt(ps,kOfxParamPropSecret,0,1);}
  if(!Q->paramGetHandle(set,"export_format",&handle,&ps))P->propSetString(ps,kOfxParamPropDefault,0,
#if JY_PLUGIN_MODE == 0
    "AAF · 内嵌音频 · 48千赫兹 / 24位"
#else
    "整轨WAV · 时间对齐 · 48千赫兹 / 24位"
#endif
  );
#endif
  return kOfxStatOK;
}
static const char *getstr(OfxImageEffectHandle effect,const char *key){
  OfxParamSetHandle set;OfxParamHandle param;char *value=NULL;
  if(E->getParamSet(effect,&set)||Q->paramGetHandle(set,key,&param,NULL)||Q->paramGetValue(param,&value))return "";
  return value?value:"";
}
static const char *selectedValue(OfxImageEffectHandle effect,const char *key){
  Session *s=sessionFor(effect);int i;if(s)for(i=0;i<6;i++)if(!strcmp(key,ownedKeys[i])&&s->values[i])return s->values[i];return getstr(effect,key);
}
static void openpath(const char *path){
  wchar_t wide[8192];if(!MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,path,-1,wide,8192))return;
  ShellExecuteW(NULL,L"\x006f\x0070\x0065\x006e",wide,NULL,NULL,SW_SHOWNORMAL);
}
static int quote_arg(wchar_t *cmd,int *len,const char *text){
  wchar_t w[8192];int i,n,slashes=0,j;
  n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,text,-1,w,8192);
  if(!n||*len+2*n+4>=30000)return 0;
  if(*len)cmd[(*len)++]=L' ';cmd[(*len)++]=L'"';
  for(i=0;w[i];i++){
    if(w[i]==L'\\'){slashes++;continue;}
    if(w[i]==L'"'){for(j=0;j<2*slashes+1;j++)cmd[(*len)++]=L'\\';}
    else{for(j=0;j<slashes;j++)cmd[(*len)++]=L'\\';}
    slashes=0;cmd[(*len)++]=w[i];
  }
  for(j=0;j<2*slashes;j++)cmd[(*len)++]=L'\\';
  cmd[(*len)++]=L'"';cmd[*len]=0;return 1;
}
#ifdef JY_AUDIO_TEST
#define MessageBoxW(...) 0
#endif
static void parameterFlag(OfxImageEffectHandle effect,const char *key,const char *flag,int value){
  OfxParamSetHandle set;OfxParamHandle param;OfxPropertySetHandle props;
  if(!E->getParamSet(effect,&set)&&!Q->paramGetHandle(set,key,&param,&props))P->propSetInt(props,flag,0,value);
}
static void showDetails(OfxImageEffectHandle effect,int show){
  const char *keys[]={"task_status","refresh_status",
#if JY_PLUGIN_MODE != 3
  "open_report",
#endif
  NULL};int i;
  for(i=0;keys[i];i++)parameterFlag(effect,keys[i],kOfxParamPropSecret,!show);

}
static int workerBusy(void){
  if(!activeWorker)return 0;
  if(WaitForSingleObject(activeWorker,0)==WAIT_TIMEOUT)return 1;
  CloseHandle(activeWorker);activeWorker=NULL;return 0;
}
static OfxStatus launchJob(OfxImageEffectHandle effect,int inspection){
#if JY_PLUGIN_MODE >= 0
  if(inspection!=JY_PLUGIN_MODE&&!(inspection==1&&JY_PLUGIN_MODE!=3))return kOfxStatErrUnsupported;
#endif
  wchar_t cmd[30000]={0},python[8192];int len=0,i,count=10,mode=0;long long numeric=0;char jobID[64],handles[2]="0";OfxParamSetHandle settingSet;OfxParamHandle setting;SYSTEMTIME st;static LONG jobSerial;
  STARTUPINFOW startup={0};PROCESS_INFORMATION process={0};
  const char *source=getstr(effect,"source_path"),*output=getstr(effect,"output_path");
  const char *args[]={PYTHON_EXE,WORKER_PATH,"--source",source,"--output",output,"--job-id",jobID,"--handles",handles,inspection==2?"--stems":inspection==3?"--batch-stems":"--inspect"};
  if(workerBusy()){showDetails(effect,1);setString(effect,"task_status","已有任务运行中，请等待完成后刷新状态");return kOfxStatOK;}
  reconcileSession(effect);
  source=selectedValue(effect,inspection==3?"batch_source_path":"source_path");output=selectedValue(effect,"output_path");args[3]=source;args[5]=output;
  showDetails(effect,1);
  GetLocalTime(&st);snprintf(jobID,sizeof(jobID),"%04d%02d%02d-%02d%02d%02d-%08lx",st.wYear,st.wMonth,st.wDay,st.wHour,st.wMinute,st.wSecond,(unsigned long)(GetTickCount()+(DWORD)InterlockedIncrement(&jobSerial)*0x9e3779b9u));
  if(!E->getParamSet(effect,&settingSet)&&!Q->paramGetHandle(settingSet,"handles_mode",&setting,NULL)&&!Q->paramGetValue(setting,&numeric))mode=(int)numeric;
  handles[0]=mode==1?'2':mode==2?'5':'0';
  if(inspection)count=11;
  if(!source[0]||!output[0]){
    setString(effect,"task_status","请选择单集草稿目录和输出目录");
    MessageBoxW(NULL,L"\x8bf7\x586b\x5199\x5355\x96c6\x8349\x7a3f\x76ee\x5f55\x548c\x0041\x0041\x0046\x8f93\x51fa\x76ee\x5f55\x3002",L"\x526a\x6620\x6df7\x97f3\x4ea4\x4e92",MB_OK|MB_ICONINFORMATION);return kOfxStatOK;}
  for(i=0;i<count;i++)if(!quote_arg(cmd,&len,args[i]))return kOfxStatErrValue;
  if(!MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,PYTHON_EXE,-1,python,8192))return kOfxStatErrValue;
  startup.cb=sizeof(startup);
  if(!CreateProcessW(python,cmd,NULL,NULL,FALSE,CREATE_NO_WINDOW,NULL,NULL,&startup,&process)){
    setString(effect,"task_status","后台启动失败，请检查Python运行环境");
    logline("worker launch failed win32=%lu",(unsigned long)GetLastError());
    MessageBoxW(NULL,L"\x65e0\x6cd5\x542f\x52a8\x0041\x0041\x0046\x540e\x53f0\xff0c\x8bf7\x68c0\x67e5\x8fd0\x884c\x73af\x5883\x3002",L"\x526a\x6620\x6df7\x97f3\x4ea4\x4e92",MB_OK|MB_ICONERROR);return kOfxStatFailed;}
  logline("AAF job dispatched pid=%lu inspect=%d job=%s",(unsigned long)process.dwProcessId,inspection,jobID);
  strcpy(activeJobID,jobID);
  setString(effect,"last_job",jobID);
  setString(effect,"task_status",inspection==1?"正在检查工程，请稍后刷新状态":inspection==2?"正在导出本集音频轨，请稍后刷新状态":inspection==3?"正在批量导出多集音频轨，请稍后刷新状态":"正在导出AAF，请稍后刷新状态");
  CloseHandle(process.hThread);activeWorker=process.hProcess;
  return kOfxStatOK;
}
/* Native folder selection; called only for explicit user button events. */
typedef int (CALLBACK *JYBrowseCallback)(HWND,UINT,LPARAM,LPARAM);
typedef struct JYBrowseInfo {
  HWND owner;const void *root;wchar_t *display;const wchar_t *title;
  UINT flags;JYBrowseCallback callback;LPARAM data;int image;
} JYBrowseInfo;
typedef void *(WINAPI *JYBrowseFn)(JYBrowseInfo *);
typedef BOOL (WINAPI *JYPathFn)(const void *,wchar_t *);
typedef BOOL (WINAPI *JYPathExFn)(const void *,wchar_t *,DWORD,DWORD);
typedef HRESULT (WINAPI *JYCoInitFn)(LPVOID,DWORD);
typedef void (WINAPI *JYCoUninitFn)(void);
typedef void (WINAPI *JYCoFreeFn)(LPVOID);
__declspec(dllimport) int WINAPI WideCharToMultiByte(UINT,DWORD,LPCWSTR,int,LPSTR,int,LPCSTR,BOOL *);
__declspec(dllimport) LRESULT WINAPI SendMessageW(HWND,UINT,WPARAM,LPARAM);

#ifdef JY_AUDIO_TEST
static wchar_t testFolder[32768];
OfxExport void JYTestSetFolder(const wchar_t *path){
  int i=0;while(path&&path[i]&&i<32767){testFolder[i]=path[i];i++;}testFolder[i]=0;
}
#endif
static int CALLBACK folderCallback(HWND window,UINT msg,LPARAM param,LPARAM initial){
  (void)param;
  /* BFFM_INITIALIZED / BFFM_SETSELECTIONW */
  if(msg==1&&initial){SendMessageW(window,0x467,1,initial);SendMessageW(window,0x46a,1,initial);}
  return 0;
}
static int nativeFolder(const wchar_t *title,const char *initial,wchar_t *selected){
#ifdef JY_AUDIO_TEST
  int i=0;(void)title;(void)initial;
  while(testFolder[i]){selected[i]=testFolder[i];i++;}selected[i]=0;
  return i?1:0;
#else
  wchar_t system[MAX_PATH],library[MAX_PATH],display[MAX_PATH],start[32768];
  HMODULE shell=NULL,ole=NULL;void *item=NULL;HRESULT hr;int ok=-1,initialized=0;
  JYBrowseFn browse;JYPathFn path;JYPathExFn pathEx;
  JYCoInitFn init;JYCoUninitFn uninit;JYCoFreeFn release;
  JYBrowseInfo info={0};
  UINT n=GetSystemDirectoryW(system,MAX_PATH);
  if(!n||n>MAX_PATH-20)return -1;
  memcpy(library,system,(n+1)*sizeof(wchar_t));
  {const wchar_t *suffix=L"\\shell32.dll";int i=0;while(suffix[i]){library[n+i]=suffix[i];i++;}library[n+i]=0;}
  shell=LoadLibraryW(library);if(!shell)return -1;
  memcpy(library,system,(n+1)*sizeof(wchar_t));
  {const wchar_t *suffix=L"\\ole32.dll";int i=0;while(suffix[i]){library[n+i]=suffix[i];i++;}library[n+i]=0;}
  ole=LoadLibraryW(library);if(!ole)goto done;
  browse=(JYBrowseFn)GetProcAddress(shell,"SHBrowseForFolderW");
  path=(JYPathFn)GetProcAddress(shell,"SHGetPathFromIDListW");
  pathEx=(JYPathExFn)GetProcAddress(shell,"SHGetPathFromIDListEx");
  init=(JYCoInitFn)GetProcAddress(ole,"CoInitializeEx");
  uninit=(JYCoUninitFn)GetProcAddress(ole,"CoUninitialize");
  release=(JYCoFreeFn)GetProcAddress(ole,"CoTaskMemFree");
  if(!browse||(!path&&!pathEx)||!init||!uninit||!release)goto done;
  hr=init(NULL,2);initialized=hr>=0;
  info.owner=GetActiveWindow();info.display=display;info.title=title;
  /* File-system directories + edit box; new dialog only on an STA thread. */
  info.flags=1|0x10|(initialized?0x40:0);
  if(MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,initial,-1,start,32768)){
    info.callback=folderCallback;info.data=(LPARAM)start;
  }
  item=browse(&info);
  if(!item){ok=0;goto cleanup;}
  if(pathEx?pathEx(item,selected,32768,0):path(item,selected))ok=1;
cleanup:
  if(item)release(item);
  if(initialized)uninit();
done:
  if(ole)FreeLibrary(ole);if(shell)FreeLibrary(shell);return ok;
#endif
}
/* Local recent folders, independent of project parameter persistence. */
__declspec(dllimport) DWORD WINAPI GetPrivateProfileStringW(LPCWSTR,LPCWSTR,LPCWSTR,LPWSTR,DWORD,LPCWSTR);
__declspec(dllimport) BOOL WINAPI WritePrivateProfileStringW(LPCWSTR,LPCWSTR,LPCWSTR,LPCWSTR);
__declspec(dllimport) BOOL WINAPI MoveFileExW(LPCWSTR,LPCWSTR,DWORD);
static LONG memorySerial;
static int memoryFile(wchar_t *path){
  const wchar_t *directory=L"\\JYMixBridge",*file=JY_MEMORY_NAME;DWORD n;int i;
  n=GetEnvironmentVariableW(L"LOCALAPPDATA",path,MAX_PATH-50);if(!n||n>=MAX_PATH-50)return 0;
  for(i=0;directory[i];i++)path[n+i]=directory[i];path[n+i]=0;n+=i;
  CreateDirectoryW(path,NULL);
  for(i=0;file[i];i++)path[n+i]=file[i];path[n+i]=0;return 1;
}
static int readMemory(const char *key,char *value,int size){
  wchar_t path[MAX_PATH],widekey[64],saved[32768];value[0]=0;
  if(!memoryFile(path)||!MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,key,-1,widekey,64))return 0;
  if(!GetPrivateProfileStringW(L"paths",widekey,L"",saved,32768,path))return 0;
  return WideCharToMultiByte(CP_UTF8,0,saved,-1,value,size,NULL,NULL)>0;
}
static int saveMemory(const char *key,const char *value){
  wchar_t path[MAX_PATH],temp[MAX_PATH],widekey[64],widevalue[32768],check[32768];
  char temp8[MAX_PATH];HANDLE mutex;DWORD wait;int ok=0;FILE *f;
  if(!memoryFile(path)||!MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,key,-1,widekey,64)||
     !MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,value,-1,widevalue,32768))return 0;
  mutex=CreateMutexW(NULL,FALSE,L"Local\\JYMixBridgePathMemory");if(!mutex)return 0;
  wait=WaitForSingleObject(mutex,1000);
  if(wait!=WAIT_OBJECT_0&&wait!=WAIT_ABANDONED){CloseHandle(mutex);return 0;}
  if(!WideCharToMultiByte(CP_UTF8,0,path,-1,temp8,MAX_PATH-35,NULL,NULL))goto done;
  {int length=(int)strlen(temp8);snprintf(temp8+length,sizeof(temp8)-length,".%lu-%ld.tmp",(unsigned long)GetCurrentProcessId(),InterlockedIncrement(&memorySerial));}
  if(!MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,temp8,-1,temp,MAX_PATH))goto done;
  if(!CopyFileW(path,temp,FALSE)){
    if(GetLastError()!=ERROR_FILE_NOT_FOUND)goto done;
    f=_wfopen(temp,L"wb");if(!f)goto done;fwrite("\xff\xfe",1,2,f);fclose(f);
  }
  if(!WritePrivateProfileStringW(L"paths",widekey,widevalue,temp))goto cleanup;
  WritePrivateProfileStringW(NULL,NULL,NULL,temp);
  GetPrivateProfileStringW(L"paths",widekey,L"",check,32768,temp);
  {int i=0;while(widevalue[i]&&widevalue[i]==check[i])i++;if(widevalue[i]!=check[i])goto cleanup;}
  ok=MoveFileExW(temp,path,9)!=0;
cleanup:
  if(!ok)DeleteFileW(temp); /* Only our new temporary preference file. */
done:
  ReleaseMutex(mutex);CloseHandle(mutex);return ok;
}
static OfxStatus setString(OfxImageEffectHandle effect,const char *key,const char *value){
  OfxParamSetHandle set;OfxParamHandle param;OfxStatus status;
  if(!Q->paramSetValue)return kOfxStatErrUnsupported;
  if(E->getParamSet(effect,&set)||Q->paramGetHandle(set,key,&param,NULL))return kOfxStatErrBadHandle;
  {Session *owned=sessionFor(effect);int wasSyncing=owned?owned->syncing:0;
  if(owned)owned->syncing=1;
  status=Q->paramSetValue(param,value);
  if(!status&&strcmp(getstr(effect,key),value))status=kOfxStatFailed;
  if(!status)rememberValue(effect,key,value);
  if(owned)owned->syncing=wasSyncing;}
  return status;
}
static void reconcileSession(OfxImageEffectHandle effect){
  Session *s=sessionFor(effect);int i;if(!s||s->syncing)return;s->syncing=1;
  for(i=0;i<3;i++)if(s->values[i]&&strcmp(getstr(effect,ownedKeys[i]),s->values[i])){
    OfxParamSetHandle set;OfxParamHandle param;
    if(!E->getParamSet(effect,&set)&&!Q->paramGetHandle(set,ownedKeys[i],&param,NULL)){Q->paramSetValue(param,s->values[i]);logline("reconciled host replay key=%s",ownedKeys[i]);}}
  s->syncing=0;
}
static void projectSummary(OfxImageEffectHandle effect){
  const char *path=getstr(effect,"source_path"),*name=path,*p;char summary[32768];
  for(p=path;*p;p++)if((*p=='/'||*p=='\\')&&p[1])name=p+1;
  snprintf(summary,sizeof(summary),"所选工程：%s（手选或已保存目录）",name[0]?name:"未选择");setString(effect,"source_origin",summary);
}
static OfxStatus restoreMemory(OfxImageEffectHandle effect,int explicitRequest){
  char saved[32768];int emptySource=!getstr(effect,"source_path")[0];OfxStatus status=kOfxStatOK;
  if((explicitRequest||emptySource)&&readMemory("source_path",saved,sizeof(saved)))status=setString(effect,"source_path",saved);
  if((explicitRequest||!getstr(effect,"output_path")[0]||
      (emptySource&&!strcmp(getstr(effect,"output_path"),DEFAULT_OUTPUT)))&&readMemory("output_path",saved,sizeof(saved))){
    OfxStatus second=setString(effect,"output_path",saved);if(second)status=second;
  }
  if(status)logline("recent directory restore not accepted status=%d",status);
  return status;
}
static void existingInitial(const char *current,const char *key,char *result,int size){
  wchar_t wide[32768];char saved[32768];const char *input=current;int pass,i;
  result[0]=0;
  for(pass=0;pass<2;pass++){
    if(pass){if(!readMemory(key,saved,sizeof(saved)))continue;input=saved;}
    if(!input[0]||!MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,input,-1,wide,32768))continue;
    for(;;){
      DWORD attributes=GetFileAttributesW(wide);
      if(attributes!=INVALID_FILE_ATTRIBUTES&&(attributes&FILE_ATTRIBUTE_DIRECTORY)){
        WideCharToMultiByte(CP_UTF8,0,wide,-1,result,size,NULL,NULL);return;
      }
      i=0;while(wide[i])i++;while(i>0&&wide[i-1]!=L'\\'&&wide[i-1]!=L'/')i--;
      if(i<3)break;if(i==3){if(!wide[3])break;wide[3]=0;}else wide[i-1]=0;
    }
  }
}

static OfxStatus chooseFolder(OfxImageEffectHandle effect,int output){
  wchar_t selected[32768];char utf8[32768],initial[32768];OfxParamSetHandle set;
  OfxParamHandle param;OfxStatus status;int picked;
  const char *key=output==2?"batch_source_path":output?"output_path":"source_path";
  const wchar_t *title=output==2?L"\x9009\x62e9\x5305\x542b\x591a\x96c6\x8349\x7a3f\x7684\x7236\x76ee\x5f55":output?L"\x9009\x62e9\x0041\x0041\x0046\x8f93\x51fa\x6587\x4ef6\x5939":L"\x9009\x62e9\x5177\x4f53\x4e00\x96c6\x7684\x526a\x6620\x8349\x7a3f\x6587\x4ef6\x5939";
  if(!Q->paramSetValue)return kOfxStatErrUnsupported;
  existingInitial(selectedValue(effect,key),key,initial,sizeof(initial));
  logline("directory chooser requested key=%s",key);
  picked=nativeFolder(title,initial,selected);
  logline("directory chooser result key=%s result=%d",key,picked);
  if(picked==0)return kOfxStatOK;
  if(picked<0){
    MessageBoxW(NULL,L"\x65e0\x6cd5\x6253\x5f00\x6587\x4ef6\x5939\x9009\x62e9\x6846\x3002",L"AAF",MB_OK|MB_ICONERROR);return kOfxStatFailed;
  }
  if(!WideCharToMultiByte(CP_UTF8,0,selected,-1,utf8,sizeof(utf8),NULL,NULL))return kOfxStatErrValue;
  if(E->getParamSet(effect,&set)||Q->paramGetHandle(set,key,&param,NULL))return kOfxStatErrBadHandle;
  status=setString(effect,key,utf8);
  if(status||strcmp(getstr(effect,key),utf8)){
    logline("folder parameter writeback failed key=%s status=%d",key,status);
    MessageBoxW(NULL,L"\x526a\x6620\x672a\x4fdd\x5b58\x9009\x4e2d\x7684\x8def\x5f84\xff0c\x8bf7\x6682\x52ff\x5bfc\x51fa\x3002",L"AAF",MB_OK|MB_ICONERROR);
    return status?status:kOfxStatFailed;
  }
  if(!saveMemory(key,utf8)){
    setString(effect,"task_status","路径已选中，但本机目录记忆写入失败");
    logline("local path memory save failed key=%s",key);
  }else setString(effect,"task_status","已记住本机目录；请检查工程后导出");
  setString(effect,"last_job","");
  if(!output)projectSummary(effect);
  setString(effect,"task_status","目录已切换；请检查或导出所选工程");
  logline("folder selected and parameter verified key=%s",key);return kOfxStatOK;
}

static OfxStatus fillOutput(OfxImageEffectHandle effect){
  OfxParamSetHandle set;OfxParamHandle p;
  if(getstr(effect,"output_path")[0])return kOfxStatOK;
  if(E->getParamSet(effect,&set)||Q->paramGetHandle(set,"output_path",&p,NULL)||!Q->paramSetValue)return kOfxStatErrUnsupported;
  return Q->paramSetValue(p,DEFAULT_OUTPUT);
}

static int jobPath(OfxImageEffectHandle effect,const char *file,char *path,int size){
  const char *id=selectedValue(effect,"last_job");char base[32768];wchar_t baseWide[32768];DWORD length;int i;
  if(strlen(id)!=24)return 0;
  for(i=0;i<24;i++)if(i==8||i==15){if(id[i]!='-')return 0;}else if(!((id[i]>='0'&&id[i]<='9')||(i>15&&id[i]>='a'&&id[i]<='f')))return 0;
  length=GetEnvironmentVariableW(L"LOCALAPPDATA",baseWide,32768);
  if(!length||length>=32768||!WideCharToMultiByte(CP_UTF8,0,baseWide,-1,base,sizeof(base),NULL,NULL))return 0;
  return snprintf(path,size,"%s\\JYMixBridge\\%s%s%s",base,id,file[0]?"\\":"",file)<size;
}
static OfxStatus refreshStatus(OfxImageEffectHandle effect){
  char path[1024],text[8192];wchar_t wide[2048];FILE *f;size_t n;
  if(!jobPath(effect,"任务结果.txt",path,sizeof(path)))return setString(effect,"task_status","尚未启动本次任务");
  if(!MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,path,-1,wide,2048))return kOfxStatErrValue;
  f=_wfopen(wide,L"rb");if(!f){
    if(!strcmp(selectedValue(effect,"last_job"),activeJobID))return setString(effect,"task_status",workerBusy()?"任务处理中，请稍后刷新":"后台已结束，但未生成结果；请查看运行环境或重新检查工程");
    return setString(effect,"task_status","未找到任务结果，无法确认运行状态；可重新检查工程");
  }
  n=fread(text,1,sizeof(text)-1,f);fclose(f);text[n]=0;
  {char *newline=strpbrk(text,"\r\n");if(newline)*newline=0;}
  return setString(effect,"task_status",text[0]?text:"结果尚未写完，请稍后刷新");
}

static void openResult(OfxImageEffectHandle effect){
  char file[2048],target[32768];wchar_t wide[32768];FILE *f;size_t n;DWORD attrs;
  reconcileSession(effect);
  if(jobPath(effect,"结果目录.txt",file,sizeof(file))&&MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,file,-1,wide,32768)&&(f=_wfopen(wide,L"rb"))){
    n=fread(target,1,sizeof(target)-1,f);fclose(f);target[n]=0;
    if(MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,target,-1,wide,32768)&&(attrs=GetFileAttributesW(wide))!=INVALID_FILE_ATTRIBUTES&&(attrs&FILE_ATTRIBUTE_DIRECTORY)){openpath(target);return;}
  }
  openpath(getstr(effect,"output_path"));
}
typedef struct Img {OfxPropertySetHandle h;unsigned char *data;int b[4],stride,bpp;} Img;
static int imageInfo(Img *im) {
  void *d=NULL;char *depth=NULL,*comp=NULL;
  if(P->propGetPointer(im->h,kOfxImagePropData,0,&d)!=kOfxStatOK||!d)return 0;
  if(P->propGetIntN(im->h,kOfxImagePropBounds,4,im->b)!=kOfxStatOK)return 0;
  if(P->propGetInt(im->h,kOfxImagePropRowBytes,0,&im->stride)!=kOfxStatOK)return 0;
  if(P->propGetString(im->h,kOfxImageEffectPropPixelDepth,0,&depth)!=kOfxStatOK||!depth)return 0;
  if(P->propGetString(im->h,kOfxImageEffectPropComponents,0,&comp)!=kOfxStatOK||!comp||strcmp(comp,kOfxImageComponentRGBA))return 0;
  im->bpp=!strcmp(depth,kOfxBitDepthByte)?4:!strcmp(depth,kOfxBitDepthShort)?8:!strcmp(depth,kOfxBitDepthFloat)?16:0;
  im->data=d;return im->bpp>0&&im->b[2]>=im->b[0]&&im->b[3]>=im->b[1];
}
static OfxStatus render(OfxImageEffectHandle effect,OfxPropertySetHandle in) {
  OfxImageClipHandle source=NULL,output=NULL;Img a={0},b={0};double time=0;
  int w[4],x,y;OfxStatus s=kOfxStatFailed;
  if(P->propGetDouble(in,kOfxPropTime,0,&time)!=kOfxStatOK||
     P->propGetIntN(in,kOfxImageEffectPropRenderWindow,4,w)!=kOfxStatOK)return kOfxStatErrValue;
  if(E->clipGetHandle(effect,"Source",&source,NULL)!=kOfxStatOK||
     E->clipGetHandle(effect,"Output",&output,NULL)!=kOfxStatOK)return kOfxStatErrBadHandle;
  if(E->clipGetImage(source,time,NULL,&a.h)!=kOfxStatOK)goto done;
  if(E->clipGetImage(output,time,NULL,&b.h)!=kOfxStatOK)goto done;
  if(!imageInfo(&a)||!imageInfo(&b)||a.bpp!=b.bpp){s=kOfxStatErrUnsupported;goto done;}
  if(w[0]<b.b[0])w[0]=b.b[0];if(w[1]<b.b[1])w[1]=b.b[1];
  if(w[2]>b.b[2])w[2]=b.b[2];if(w[3]>b.b[3])w[3]=b.b[3];
  for(y=w[1];y<w[3];y++){
    if(E->abort&&E->abort(effect)){s=kOfxStatOK;goto done;}
    for(x=w[0];x<w[2];x++){
      unsigned char *dst=b.data+(ptrdiff_t)(y-b.b[1])*b.stride+(ptrdiff_t)(x-b.b[0])*b.bpp;
      if(x>=a.b[0]&&x<a.b[2]&&y>=a.b[1]&&y<a.b[3])
        memcpy(dst,a.data+(ptrdiff_t)(y-a.b[1])*a.stride+(ptrdiff_t)(x-a.b[0])*a.bpp,b.bpp);
      else memset(dst,0,b.bpp);
    }
  }
  s=kOfxStatOK;
done:
  if(a.h)E->clipReleaseImage(a.h);if(b.h)E->clipReleaseImage(b.h);
  if(InterlockedIncrement(&renderLogs)<=6)logline("render time=%.3f status=%d",time,s);
  return s;
}
static OfxStatus entry(const char *action,const void *handle,OfxPropertySetHandle in,OfxPropertySetHandle out){
  OfxImageEffectHandle effect=(OfxImageEffectHandle)handle;char *name=NULL,*reason=NULL;
  if(!action)return kOfxStatErrValue;
  if(strcmp(action,kOfxImageEffectActionRender))logline("action %s",action);
  if(!strcmp(action,kOfxActionLoad))return load();
  if(!strcmp(action,kOfxActionUnload)){if(activeWorker){CloseHandle(activeWorker);activeWorker=NULL;}return kOfxStatOK;}
  if(!P||!E||!Q)return kOfxStatErrMissingHostFeature;
  if(!strcmp(action,kOfxActionDescribe))return describe(effect);
  if(!strcmp(action,kOfxImageEffectActionDescribeInContext))return context(effect,in);
  if(!strcmp(action,kOfxActionCreateInstance)){restoreMemory(effect,0);projectSummary(effect);return kOfxStatOK;}
  /* Never mutate parameters from EndInstanceChanged: hosts can replay this action. */
  if(!strcmp(action,kOfxActionEndInstanceChanged))return kOfxStatOK;
  if(!strcmp(action,kOfxActionDestroyInstance)){forgetSession(effect);return kOfxStatOK;}
  if(!strcmp(action,kOfxActionInstanceChanged)){
    if(!in||P->propGetString(in,kOfxPropName,0,&name)||!name)return kOfxStatOK;
    P->propGetString(in,kOfxPropChangeReason,0,&reason);
    logline("parameter event name=%s reason=%s",name,reason?reason:"missing");
    if(!reason||strcmp(reason,kOfxChangeUserEdited))return kOfxStatOK;
    if(!strcmp(name,"toggle_details")){
      OfxParamSetHandle set;OfxParamHandle param;OfxPropertySetHandle props;int hidden=1;
      if(!E->getParamSet(effect,&set)&&!Q->paramGetHandle(set,"task_status",&param,&props))P->propGetInt(props,kOfxParamPropSecret,0,&hidden);
      showDetails(effect,hidden);if(hidden)refreshStatus(effect);return kOfxStatOK;
    }
    if(!strcmp(name,"choose_source"))return chooseFolder(effect,0);
    if(!strcmp(name,"choose_output"))return chooseFolder(effect,1);
    if(!strcmp(name,"choose_batch_source"))return chooseFolder(effect,2);
    if(!strcmp(name,"export_stems"))return launchJob(effect,2);
    if(!strcmp(name,"export_batch_stems"))return launchJob(effect,3);
    if(!strcmp(name,"open_panel"))return kOfxStatOK;
    if(!strcmp(name,"open_output")){
      openResult(effect);return kOfxStatOK;
    }
    if(!strcmp(name,"restore_paths"))return restoreMemory(effect,1);
    if(!strcmp(name,"refresh_status"))return refreshStatus(effect);
    if(!strcmp(name,"inspect_project"))return launchJob(effect,1);
    if(!strcmp(name,"open_report")){char report[1024];wchar_t wide[2048];DWORD attributes;
      if(jobPath(effect,"工程检查报告.md",report,sizeof(report))&&MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,report,-1,wide,2048)&&(attributes=GetFileAttributesW(wide))!=INVALID_FILE_ATTRIBUTES&&!(attributes&FILE_ATTRIBUTE_DIRECTORY))openpath(report);
      else{showDetails(effect,1);setString(effect,"task_status","检查报告尚未生成，请先检查工程并等待完成");}return kOfxStatOK;}
    if(!strcmp(name,"export_aaf"))return launchJob(effect,0);
    if(!strcmp(name,"fill_output"))return fillOutput(effect);
    if(!strcmp(name,"open_jobs")){
      char path[1024];refreshStatus(effect);if(jobPath(effect,"",path,sizeof(path)))openpath(path);
    }
    return kOfxStatOK;
  }
  if(!strcmp(action,kOfxImageEffectActionRender))return render(effect,in);
  return kOfxStatReplyDefault;
}
static OfxPlugin plugin={kOfxImageEffectPluginApi,1,JY_PLUGIN_ID,0,JY_VERSION_MINOR,setHost,entry};
OfxExport int OfxGetNumberOfPlugins(void){logline("plugin %s enumerate",JY_PLUGIN_LABEL);return 1;}
OfxExport OfxPlugin *OfxGetPlugin(int index){logline("plugin %s metadata index=%d",JY_PLUGIN_LABEL,index);return index==0?&plugin:NULL;}

#ifdef JY_AUDIO_TEST
OfxExport int JYTestQuoteArg(wchar_t *cmd,int *len,const char *text){return quote_arg(cmd,len,text);}
#endif

#ifdef JY_AUDIO_TEST
OfxExport void JYTestInitial(const char *current,const char *key,char *result,int size){existingInitial(current,key,result,size);}
#endif
