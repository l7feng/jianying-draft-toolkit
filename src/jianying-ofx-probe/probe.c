/* JY OFX interface probe, project 71. Uses upstream OpenFX headers (BSD-3-Clause).
 * No project writes, network requests, or audio export. */
#include <windows.h>
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
  logline("probe v0.1 load");
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
  P->propSetString(ps,kOfxPropLabel,0,"JY Interface Probe");
  P->propSetString(ps,kOfxImageEffectPluginPropGrouping,0,"JY Diagnostics");
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
static OfxStatus context(OfxImageEffectHandle effect,OfxPropertySetHandle in) {
  OfxPropertySetHandle ps=NULL; OfxParamSetHandle params=NULL;
  const char *clips[]={"Source","Output"}; int i; OfxStatus s;
  dumpProps(in,"context");
  for(i=0;i<2;i++){
    s=E->clipDefine(effect,clips[i],&ps);if(s!=kOfxStatOK)return s;
    P->propSetString(ps,kOfxImageEffectPropSupportedComponents,0,kOfxImageComponentRGBA);
    P->propSetInt(ps,kOfxImageEffectPropSupportsTiles,0,0);
  }
  s=E->getParamSet(effect,&params);if(s!=kOfxStatOK)return s;
  s=Q->paramDefine(params,kOfxParamTypeDouble,"probe_level",&ps);if(s!=kOfxStatOK)return s;
  P->propSetString(ps,kOfxPropLabel,0,"Probe value (no image change)");
  P->propSetDouble(ps,kOfxParamPropDefault,0,0.5);
  P->propSetDouble(ps,kOfxParamPropMin,0,0.0);P->propSetDouble(ps,kOfxParamPropMax,0,1.0);
  P->propSetDouble(ps,kOfxParamPropDisplayMin,0,0.0);P->propSetDouble(ps,kOfxParamPropDisplayMax,0,1.0);
  s=Q->paramDefine(params,kOfxParamTypePushButton,"probe_button",&ps);if(s!=kOfxStatOK)return s;
  P->propSetString(ps,kOfxPropLabel,0,"Record capabilities");
  s=Q->paramDefine(params,kOfxParamTypeString,"param_draft_path",&ps);if(s!=kOfxStatOK)return s;
  P->propSetString(ps,kOfxPropLabel,0,"Draft path probe (leave empty)");
  P->propSetString(ps,kOfxParamPropDefault,0,"");
  P->propSetString(ps,kOfxParamPropHint,0,"Diagnostic only. Records presence and length, never writes a draft.");
  return kOfxStatOK;
}
static void inspectDraft(OfxImageEffectHandle effect) {
  OfxParamSetHandle ps=NULL;OfxParamHandle param=NULL;char *v=NULL;
  if(E->getParamSet(effect,&ps)==kOfxStatOK &&
     Q->paramGetHandle(ps,"param_draft_path",&param,NULL)==kOfxStatOK &&
     Q->paramGetValue(param,&v)==kOfxStatOK)
    logline("draft_path present=%d length=%lu",v&&v[0]?1:0,v?(unsigned long)strlen(v):0);
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
static OfxStatus entry(const char *action,const void *handle,OfxPropertySetHandle in,OfxPropertySetHandle out) {
  OfxImageEffectHandle e=(OfxImageEffectHandle)handle;char *name=NULL;
  if(!action)return kOfxStatErrValue;
  if(strcmp(action,kOfxImageEffectActionRender))logline("action %s",action);
  if(!strcmp(action,kOfxActionLoad))return load();
  if(!strcmp(action,kOfxActionUnload))return kOfxStatOK;
  if(!P||!E||!Q)return kOfxStatErrMissingHostFeature;
  if(!strcmp(action,kOfxActionDescribe))return describe(e);
  if(!strcmp(action,kOfxImageEffectActionDescribeInContext))return context(e,in);
  if(!strcmp(action,kOfxActionCreateInstance)){dumpProps(in,"create");return kOfxStatOK;}
  if(!strcmp(action,kOfxActionDestroyInstance))return kOfxStatOK;
  if(!strcmp(action,kOfxActionInstanceChanged)){
    if(in&&P->propGetString(in,kOfxPropName,0,&name)==kOfxStatOK&&name)logline("changed %.100s",name);
    inspectDraft(e);if(name&&!strcmp(name,"probe_button"))dumpProps(gHost->host,"host");
    return kOfxStatOK;
  }
  if(!strcmp(action,kOfxImageEffectActionRender))return render(e,in);
  return kOfxStatReplyDefault;
}
static OfxPlugin plugin={kOfxImageEffectPluginApi,1,"local.jytools.InterfaceProbe",0,1,setHost,entry};
OfxExport int OfxGetNumberOfPlugins(void){return 1;}
OfxExport OfxPlugin *OfxGetPlugin(int index){return index==0?&plugin:NULL;}

