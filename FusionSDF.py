#Author-ahb
#Description-Export Fusion 360 design to SDF

import traceback
from pathlib import Path

import adsk.core
import adsk.fusion
import adsk.cam

from .fusionsdf.log import set_log_console, log
from .fusionsdf.sdf import SDF

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface
        console = ui.palettes.itemById('TextCommands')
        if not console.isVisible:
            console.isVisible = True
        set_log_console(console)
        log('\n\n--- FusionSDF ---\n')

        product = app.activeProduct
        design = adsk.fusion.Design.cast(product)
        title = 'FusionSDF'
        if not design:
            log('Error: No active Fusion design. Exiting.\n')
            return

        folder_dialog = ui.createFolderDialog()
        folder_dialog.title = 'Select folder to save SDF'
        dialog_result = folder_dialog.showDialog()
        if dialog_result != adsk.core.DialogResults.DialogOK:
            log('No folder selected. Exiting.\n')
            return
        sdf_dir_path = Path(folder_dialog.folder)
        if not sdf_dir_path.exists() or not sdf_dir_path.is_dir():
            log(f'Error: "{sdf_dir_path}" does not exist or is not a directory. Exiting.\n')
            return

        if sdf_dir_path.joinpath('model.sdf').exists() or sdf_dir_path.joinpath('meshes').exists():
            return_value, cancelled = ui.inputBox(f'Warning: The selected folder "{str(sdf_dir_path)}" already contains an SDF file or a meshes directory. Overwrite? Enter Y or N',
                                                  'OverwriteWarning', '')
            if return_value.upper() == 'N' or cancelled:
                log('Cancelled. Exiting.\n')
                return

        meshes_cache_path = sdf_dir_path / 'meshes_cache'
        log(f'using meshes_cache directory "{meshes_cache_path}" (if it exists)\n')
        sdf = SDF(design, meshes_cache_path)
        sdf.print()
        sdf.save(sdf_dir_path)

    except:
        if ui:
            ui.messageBox(f'Failed:\n{traceback.format_exc()}')
