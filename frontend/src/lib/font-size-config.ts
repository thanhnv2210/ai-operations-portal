// ─── Config — change these two lines when copying to a new project ─────────────
export const FONT_STORAGE_KEY = "ai-ops-portal:font-size"
export const FONT_SIZE_EVENT  = "ai-ops-portal:font-size-change"
// ──────────────────────────────────────────────────────────────────────────────

export const FONT_SIZE_MIN = 12
export const FONT_SIZE_MAX = 22

/**
 * Inline script for <head> — eliminates font-size FOUC.
 * Runs synchronously before first paint, mirrors getAutoFontSize() logic.
 */
export function getFoucScript(): string {
  return `(function(){try{
    var s=localStorage.getItem(${JSON.stringify(FONT_STORAGE_KEY)});
    var n=s?parseInt(s,10):NaN;
    if(!n||isNaN(n)){
      var w=screen.width;
      n=w<768?16:w<1280?15:w<1440?14:w<1920?15:w<2560?16:w<3840?17:18;
    }
    document.documentElement.style.fontSize=n+'px';
  }catch(e){}})();`
}
