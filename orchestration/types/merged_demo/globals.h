#ifndef DQXI_DQXI_GLOBALS_H
#define DQXI_DQXI_GLOBALS_H

#include "structs.h"

/* Named data objects of the retail executable. Each comment gives the
 * address in the original image and what the object is for. */

/* --- Save --- */
extern char g_saveDataPathPrefix[6];                 /* 0x0072D780 conf 0.80: Mount/path prefix "data:" used when building save-slot file names (Save_WriteSlotStrings, Save_DeleteSlotFiles, Fs_Forma */

/* --- Ui --- */
extern Ui_Part g_uiPartSentinel;                     /* 0x007AE8A4 conf 0.75: Sentinel 'ui part' object whose address terminates the child-part linked lists returned by the virtual +8 iterator. 25 U */

#endif /* DQXI_DQXI_GLOBALS_H */
