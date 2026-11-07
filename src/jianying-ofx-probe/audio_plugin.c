/* JY Audio Toolkit OFX, project 71. OpenFX headers: BSD-3-Clause.
 * Explicit buttons dispatch an external worker; render only copies pixels. */
#include <windows.h>
#define CP_UTF8 65001
#define MB_ERR_INVALID_CHARS 8
__declspec(dllimport) int WINAPI MultiByteToWideChar(UINT,DWORD,LPCSTR,int,LPWSTR,int);
__declspec(dllimport) HINSTANCE WINAPI ShellExecuteW(HWND,LPCWSTR,LPCWSTR,LPCWSTR,LPCWSTR,INT);
#define DEFAULT_SOURCE "\104\072\057\115\171\055\124\145\155\160\157\162\141\162\171\057\102\141\143\153\165\160\055\112\151\141\156\171\151\156\147\057\120\162\157\152\145\143\164\057\112\151\141\156\171\151\156\147\120\162\157\040\104\162\141\146\164\163"
#define DEFAULT_OUTPUT "\104\072\057\115\171\055\124\145\155\160\157\162\141\162\171\057\102\141\143\153\165\160\055\112\151\141\156\171\151\156\147\057\124\157\157\154\163\057\157\165\164"
#define DEFAULT_MANIFEST ""
#define WORKER_PATH "\104\072\134\101\151\055\106\151\154\145\163\134\122\145\160\157\163\134\107\151\164\110\165\142\134\160\164\055\141\165\144\151\157\055\164\157\157\154\153\151\164\134\163\162\143\134\152\151\141\156\171\151\156\147\055\157\146\170\055\160\162\157\142\145\134\141\165\144\151\157\137\167\157\162\153\145\162\056\160\171"
#define PYTHON_EXE "\104\072\057\101\151\055\106\151\154\145\163\057\124\157\157\154\163\057\102\165\151\154\144\105\156\166\057\160\171\063\061\062\057\160\171\164\150\157\156\167\056\145\170\145"
#define TOOLKIT_EXE "\104\072\057\101\151\055\106\151\154\145\163\057\124\157\157\154\163\057\105\170\145\057\060\062\055\345\211\252\346\230\240\345\267\245\347\250\213\345\267\245\345\205\267\345\214\205\057\152\151\141\156\171\151\156\147\055\144\162\141\146\164\055\164\157\157\154\153\151\164\055\110\055\166\064\056\062\056\061\057\345\211\252\346\230\240\345\267\245\347\250\213\345\267\245\345\205\267\345\214\205\055\110\347\211\210\056\145\170\145"

#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <stdlib.h>
#include "ofxImageEffect.h"
#include "ofxProperty.h"
static OfxHost *gHost;
static OfxPropertySuiteV1 *P;
static OfxImageEffectSuiteV1 *E;
static OfxParameterSuiteV1 *Q;
static LONG renderLogs;
static void logline(const char *fmt, ...) {
  char dir[MAX_PATH], path[MAX_PATH]; FILE *f; va_list ap; SYSTEMTIME st;
  if (!GetEnvironmentVariableA("LOCALAPPDATA", dir, MAX_PATH-24)) return;
  strcat(dir, "\\JyOfxProbe"); CreateDirectoryA(dir, NULL);
  snprintf(path, sizeof(path), "%s\\probe-%lu.log", dir, (unsigned long)GetCurrentProcessId());
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
  logline("audio toolkit v0.2 load");
  for(i=0;suites[i];i++)logline("suite %s v1=%s",suites[i],gHost->fetchSuite(gHost->host,suites[i],1)?"available":"missing");
  P=(OfxPropertySuiteV1*)gHost->fetchSuite(gHost->host,kOfxPropertySuite,1);
  E=(OfxImageEffectSuiteV1*)gHost->fetchSuite(gHost->host,kOfxImageEffectSuite,1);
  Q=(OfxParameterSuiteV1*)gHost->fetchSuite(gHost->host,kOfxParameterSuite,1);
  if(!P||!E||!Q)return kOfxStatErrMissingHostFeature;
  dumpProps(gHost->host,"host"); return kOfxStatOK;
}
static OfxStatus describe(OfxImageEffectHandle effect) {
  OfxPropertySetHandle ps=NULL;
  if(E->getPropertySet(effect,&ps)!=kOfxStatOK)return kOfxStatErrBadHandle;
  P->propSetString(ps,kOfxPropLabel,0,"JY Audio Toolkit");
  P->propSetString(ps,kOfxImageEffectPluginPropGrouping,0,"JY Audio");
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
  /* Compatibility: use plain string controls like the verified probe. */
  return kOfxStatOK;
}
static OfxStatus context(OfxImageEffectHandle effect,OfxPropertySetHandle in){
  OfxParamSetHandle set;OfxPropertySetHandle ps;int i;OfxStatus s;
  const char *clips[]={"Source","Output"};
  const char *keys[]={"export_audio","import_copy","open_toolkit","open_jobs"};
  const char *labels[]={"批量导出音频 / Export audio","导入到新草稿副本 / Import to copy","打开原工具包 / Open EXE","查看任务记录 / View jobs"};
  for(i=0;i<2;i++){s=E->clipDefine(effect,clips[i],&ps);if(s)return s;
    P->propSetString(ps,kOfxImageEffectPropSupportedComponents,0,kOfxImageComponentRGBA);
    P->propSetInt(ps,kOfxImageEffectPropSupportsTiles,0,0);}
  s=E->getParamSet(effect,&set);if(s)return s;
  if((s=strparam(set,"source_path","草稿或素材目录 / Draft or media folder",DEFAULT_SOURCE,kOfxParamStringIsDirectoryPath)))return s;
  if((s=strparam(set,"output_path","音频输出目录 / Audio output folder",DEFAULT_OUTPUT,kOfxParamStringIsDirectoryPath)))return s;
  if((s=strparam(set,"manifest_path","PT JSON或CSV清单 / Audio manifest",DEFAULT_MANIFEST,kOfxParamStringIsFilePath)))return s;
  if((s=strparam(set,"copy_path","新草稿副本目录 / New draft copy folder","",kOfxParamStringIsDirectoryPath)))return s;
  s=Q->paramDefine(set,kOfxParamTypeChoice,"export_mode",&ps);if(s)return s;
  P->propSetString(ps,kOfxPropLabel,0,"导出方式 / Export mode");
  P->propSetString(ps,kOfxParamPropChoiceOption,0,"整轨 / Tracks");
  P->propSetString(ps,kOfxParamPropChoiceOption,1,"片段 / Clips");
  P->propSetString(ps,kOfxParamPropChoiceOption,2,"整轨和片段 / Both");
  P->propSetInt(ps,kOfxParamPropDefault,0,0);
  for(i=0;i<4;i++){s=Q->paramDefine(set,kOfxParamTypePushButton,keys[i],&ps);if(s)return s;P->propSetString(ps,kOfxPropLabel,0,labels[i]);}
  return kOfxStatOK;
}
static const char *getstr(OfxImageEffectHandle effect,const char *key){
  OfxParamSetHandle set;OfxParamHandle param;char *value=NULL;
  if(E->getParamSet(effect,&set)||Q->paramGetHandle(set,key,&param,NULL)||Q->paramGetValue(param,&value))return "";
  return value?value:"";
}
static void openpath(const char *path){
  wchar_t wide[8192];if(!MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,path,-1,wide,8192))return;
  ShellExecuteW(NULL,L"open",wide,NULL,NULL,SW_SHOWNORMAL);
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
static OfxStatus launchJob(OfxImageEffectHandle effect,const char *action){
  wchar_t cmd[30000]={0},python[8192];int len=0,mode=0,i;
  STARTUPINFOW startup={0};PROCESS_INFORMATION process={0};
  OfxParamSetHandle set;OfxParamHandle param;const char *modes[]={"tracks","clips","both"};
  const char *source=getstr(effect,"source_path"),*output=getstr(effect,"output_path");
  const char *manifest=getstr(effect,"manifest_path"),*copy=getstr(effect,"copy_path");
  const char *args[]={PYTHON_EXE,WORKER_PATH,"--action",action,"--source",source,"--output",output,"--manifest",manifest,"--copy",copy,"--mode",NULL};
  if(!source[0]||(!strcmp(action,"export")&&!output[0])||(!strcmp(action,"import-copy")&&(!manifest[0]||!copy[0]))){
    MessageBoxW(NULL,L"Please fill the required source, output or import paths.",L"JY Audio Toolkit",MB_OK|MB_ICONINFORMATION);
    return kOfxStatOK;
  }
  if(!E->getParamSet(effect,&set)&&!Q->paramGetHandle(set,"export_mode",&param,NULL))Q->paramGetValue(param,&mode);
  if(mode<0||mode>2)return kOfxStatErrValue;args[13]=modes[mode];
  for(i=0;i<14;i++)if(!quote_arg(cmd,&len,args[i]))return kOfxStatErrValue;
  if(!MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,PYTHON_EXE,-1,python,8192))return kOfxStatErrValue;
  startup.cb=sizeof(startup);
  if(!CreateProcessW(python,cmd,NULL,NULL,FALSE,CREATE_NO_WINDOW,NULL,NULL,&startup,&process)){
    logline("worker launch failed win32=%lu",(unsigned long)GetLastError());
    MessageBoxW(NULL,L"Unable to start the local audio worker. Check its installed paths.",L"JY Audio Toolkit",MB_OK|MB_ICONERROR);
    return kOfxStatFailed;
  }
  logline("audio job dispatched action=%s pid=%lu",action,(unsigned long)process.dwProcessId);
  CloseHandle(process.hThread);CloseHandle(process.hProcess);
  MessageBoxW(NULL,L"Task started. Use View jobs to check the result.",L"JY Audio Toolkit",MB_OK|MB_ICONINFORMATION);
  return kOfxStatOK;
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
  if(!strcmp(action,kOfxActionLoad))return load();
  if(!strcmp(action,kOfxActionUnload))return kOfxStatOK;
  if(!P||!E||!Q)return kOfxStatErrMissingHostFeature;
  if(!strcmp(action,kOfxActionDescribe))return describe(effect);
  if(!strcmp(action,kOfxImageEffectActionDescribeInContext))return context(effect,in);
  if(!strcmp(action,kOfxActionCreateInstance)||!strcmp(action,kOfxActionDestroyInstance))return kOfxStatOK;
  if(!strcmp(action,kOfxActionInstanceChanged)){
    if(!in||P->propGetString(in,kOfxPropName,0,&name)||!name)return kOfxStatOK;
    if(P->propGetString(in,kOfxPropChangeReason,0,&reason)||!reason||strcmp(reason,kOfxChangeUserEdited))return kOfxStatOK;
    if(!strcmp(name,"export_audio"))return launchJob(effect,"export");
    if(!strcmp(name,"import_copy"))return launchJob(effect,"import-copy");
    if(!strcmp(name,"open_toolkit"))openpath(TOOLKIT_EXE);
    if(!strcmp(name,"open_jobs")){
      char path[MAX_PATH];if(GetEnvironmentVariableA("LOCALAPPDATA",path,MAX_PATH-20)){strcat(path,"\\JyOfxAudio");CreateDirectoryA(path,NULL);openpath(path);}
    }
    return kOfxStatOK;
  }
  if(!strcmp(action,kOfxImageEffectActionRender))return render(effect,in);
  return kOfxStatReplyDefault;
}
static OfxPlugin plugin={kOfxImageEffectPluginApi,1,"local.jytools.AudioToolkit",0,2,setHost,entry};
OfxExport int OfxGetNumberOfPlugins(void){logline("audio v0.2 enumerate");return 1;}
OfxExport OfxPlugin *OfxGetPlugin(int index){logline("audio v0.2 metadata index=%d",index);return index==0?&plugin:NULL;}

#ifdef JY_AUDIO_TEST
OfxExport int JYTestQuoteArg(wchar_t *cmd,int *len,const char *text){return quote_arg(cmd,len,text);}
#endif
