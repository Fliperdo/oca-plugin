import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp, Gio, GLib, GObject
import os
import sys

def export_layers(procedure, run_mode, image, drawables, config, run_data):
    file = image.get_file()
    if file is None:
        Gimp.message("Please save the image first before exporting layers.")
        return procedure.new_return_values(Gimp.PDBStatusType.CALLING_ERROR, GLib.Error())

    output_folder = os.path.join(os.path.dirname(file.get_path()), "images")
    os.makedirs(output_folder, exist_ok=True)

    layers = image.get_layers()

    for i, layer in enumerate(layers):
        filename = f"layer_{str(i+1).zfill(3)}_{layer.get_name().replace(' ', '_')}.png"
        filepath = os.path.join(output_folder, filename)

        temp_image = image.duplicate()
        temp_layers = temp_image.get_layers()
        temp_layer = temp_layers[i]
        temp_image.set_active_layer(temp_layer)
        flattened = temp_image.flatten()

        out_file = Gio.File.new_for_path(filepath)
        Gimp.get_pdb().run_procedure('file-png-save', [
            GLib.Value(Gimp.RunMode.__gtype__, Gimp.RunMode.NONINTERACTIVE),
            GLib.Value(Gimp.Image.__gtype__, temp_image),
            GLib.Value(Gimp.Drawable.__gtype__, flattened),
            GLib.Value(Gio.File.__gtype__, out_file)
        ])

        temp_image.delete()
        print(f"Saved: {filepath}")

    print(f"Done! {len(layers)} layers exported to {output_folder}")
    return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())


class ExportLayers(Gimp.PlugIn):
    def do_query_procedures(self):
        return ["export-layers"]

    def do_create_procedure(self, name):
        procedure = Gimp.ImageProcedure.new(
            self, name,
            Gimp.PDBProcType.PLUGIN,
            export_layers, None
        )
        procedure.set_menu_label("Export Layers")
        procedure.add_menu_path("<Image>/Filters/")
        procedure.set_documentation(
            "Export all layers as PNG files",
            "Exports each layer as a separate PNG into an images folder",
            name
        )
        procedure.set_attribution("spyjay19", "", "2026")
        return procedure


GObject.type_register(ExportLayers)
Gimp.main(ExportLayers.__gtype__, sys.argv)