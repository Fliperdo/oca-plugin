#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json
import os
import tempfile
import zipfile
import gi

gi.require_version("Gimp", "3.0")
from gi.repository import Gimp
from gi.repository import Gio
from gi.repository import GLib


PLUGIN_PROC = "file-oca-save"


def export_layers(image, temp_dir):
    layers = image.get_layers()

    for i, layer in enumerate(layers):
        filename = f"layer_{str(i+1).zfill(3)}_{layer.get_name().replace(' ', '_')}.png"
        filepath = os.path.join(temp_dir, filename)

        temp_image = image.duplicate()
        temp_layers = temp_image.get_layers()
        for j, temp_layer in enumerate(temp_layers):
            if j != i:
                temp_image.remove_layer(temp_layer)

        flattened = temp_image.flatten()
        out_file = Gio.File.new_for_path(filepath)
        success = Gimp.file_save(
            Gimp.RunMode.NONINTERACTIVE,
            temp_image,
            out_file,
            None
        )
        temp_image.delete()

        if not success:
            raise RuntimeError(f"Failed to save layer {layer.get_name()} to {filepath}")

        print(f"Saved: {filepath}")

    print(f"Done! {len(layers)} layers exported to {temp_dir}")


def oca_save_run(*args):
    try:
        print("oca_save_run arg count:", len(args))
        for i, arg in enumerate(args):
            print(f"arg[{i}] type={type(arg)} value={arg}")

        procedure = args[0]

        image = None
        for arg in args:
            if isinstance(arg, Gimp.Image):
                image = arg
                break

        file_obj = None
        for arg in args:
            if hasattr(arg, "get_path"):
                maybe_path = arg.get_path()
                if maybe_path is not None:
                    file_obj = arg
                    break

        if file_obj is None:
            return procedure.new_return_values(
                Gimp.PDBStatusType.CALLING_ERROR,
                GLib.Error.new_literal(
                    GLib.quark_from_string("oca-plugin"),
                    "Could not find export file argument.",
                    0
                )
            )

        output_path = file_obj.get_path()
        if not output_path:
            return procedure.new_return_values(
                Gimp.PDBStatusType.CALLING_ERROR,
                GLib.Error.new_literal(
                    GLib.quark_from_string("oca-plugin"),
                    "No output path was provided.",
                    0
                )
            )

        if not output_path.lower().endswith(".oca"):
            output_path += ".oca"

        content_json = {
            "format": "open-cel-animation",
            "version": 1,
            "layers": [
                {
                    "name": layer.get_name(),
                    "filename": f"images/layer_{str(i+1).zfill(3)}_{layer.get_name().replace(' ', '_')}.png"
                }
                for i, layer in enumerate(image.get_layers())
            ] if image is not None else []
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            if image is not None:
                export_layers(image, temp_dir)

            with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("content.json", json.dumps(content_json, indent=2) + "\n")

                if image is not None:
                    for filename in os.listdir(temp_dir):
                        filepath = os.path.join(temp_dir, filename)
                        zf.write(filepath, f"images/{filename}")
                        print(f"Zipped: images/{filename}")

        return procedure.new_return_values(
            Gimp.PDBStatusType.SUCCESS,
            GLib.Error()
        )

    except Exception as exc:
        print("oca_save_run exception:", repr(exc))
        procedure = args[0] if args else None
        if procedure is not None:
            return procedure.new_return_values(
                Gimp.PDBStatusType.EXECUTION_ERROR,
                GLib.Error.new_literal(
                    GLib.quark_from_string("oca-plugin"),
                    str(exc),
                    0
                )
            )
        raise


class OcaSaver(Gimp.PlugIn):
    def do_query_procedures(self):
        return [PLUGIN_PROC]

    def do_set_i18n(self, name):
        return False

    def do_create_procedure(self, name):
        if name != PLUGIN_PROC:
            return None

        procedure = Gimp.ExportProcedure.new(
            self,
            name,
            Gimp.PDBProcType.PLUGIN,
            False,
            oca_save_run,
            None,
            None
        )

        procedure.set_documentation(
            "Export as OCA",
            "Creates an MVP .oca ZIP with an empty content.json",
            name
        )
        procedure.set_attribution("Clifton Malecki", "Clifton Malecki", "2026")
        procedure.set_extensions("oca")
        procedure.set_mime_types("application/zip")
        procedure.set_menu_label("Open Cel Animation")

        return procedure


Gimp.main(OcaSaver.__gtype__, sys.argv)