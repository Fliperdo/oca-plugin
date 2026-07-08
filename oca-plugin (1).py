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
PLUGIN_PROC_LOAD = "file-oca-load"


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


def build_content_json(image, temp_dir):
    width = image.get_width()
    height = image.get_height()
    layers = image.get_layers()

    oca_layers = []
    for i, layer in enumerate(layers):
        filename = f"layer_{str(i+1).zfill(3)}_{layer.get_name().replace(' ', '_')}.png"

        oca_layers.append({
            "name": layer.get_name(),
            "type": "paintLayer",
            "fileType": "png",
            "blendingMode": "normal",
            "opacity": layer.get_opacity() / 100.0,
            "visible": layer.get_visible(),
            "position": [layer.get_offsets()[0], layer.get_offsets()[1]],
            "width": layer.get_width(),
            "height": layer.get_height(),
            "frames": [
                {
                    "name": f"images/{filename}",
                    "duration": 1
                }
            ]
        })

    return {
        "format": "open-cel-animation",
        "version": 1,
        "name": image.get_file().get_basename() if image.get_file() else "Untitled",
        "frameRate": 24,
        "width": width,
        "height": height,
        "startTime": 0,
        "endTime": len(layers),
        "colorDepth": "U8",
        "backgroundColor": [0, 0, 0, 0],
        "layers": oca_layers
    }


def import_oca(input_path):
    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(input_path, "r") as zf:
            zf.extractall(temp_dir)

        content_json_path = os.path.join(temp_dir, "content.json")
        if not os.path.exists(content_json_path):
            raise RuntimeError("No content.json found in .oca file.")

        with open(content_json_path, "r") as f:
            content = json.load(f)

        width = content.get("width", 1920)
        height = content.get("height", 1080)
        name = content.get("name", "Imported OCA")
        oca_layers = content.get("layers", [])

        image = Gimp.Image.new(width, height, Gimp.ImageType.RGBA)
        image.set_name(name)

        for layer_data in reversed(oca_layers):
            layer_name = layer_data.get("name", "Layer")
            opacity = layer_data.get("opacity", 1.0) * 100.0
            visible = layer_data.get("visible", True)
            position = layer_data.get("position", [0, 0])
            frames = layer_data.get("frames", [])

            if not frames:
                continue

            frame_filename = frames[0].get("name", "")
            frame_path = os.path.join(temp_dir, frame_filename)

            if not os.path.exists(frame_path):
                print(f"Warning: frame image not found: {frame_path}")
                continue

            frame_file = Gio.File.new_for_path(frame_path)
            loaded_image = Gimp.file_load(
                Gimp.RunMode.NONINTERACTIVE,
                frame_file
            )

            if loaded_image is None:
                print(f"Warning: could not load {frame_path}")
                continue

            loaded_layer = loaded_image.flatten()

            new_layer = Gimp.Layer.new_from_drawable(loaded_layer, image)
            new_layer.set_name(layer_name)
            new_layer.set_opacity(opacity)
            new_layer.set_visible(visible)

            image.insert_layer(new_layer, None, -1)
            new_layer.set_offsets(position[0], position[1])

            loaded_image.delete()
            print(f"Imported layer: {layer_name}")

        if image.get_layers():
            image.set_active_layer(image.get_layers()[0])

        print(f"Done! Imported {len(oca_layers)} layers from {input_path}")
        return image


def oca_load_run(*args):
    try:
        print("oca_load_run arg count:", len(args))
        for i, arg in enumerate(args):
            print(f"arg[{i}] type={type(arg)} value={arg}")

        procedure = args[0]

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
                    "Could not find input file argument.",
                    0
                )
            )

        input_path = file_obj.get_path()
        if not input_path:
            return procedure.new_return_values(
                Gimp.PDBStatusType.CALLING_ERROR,
                GLib.Error.new_literal(
                    GLib.quark_from_string("oca-plugin"),
                    "No input path was provided.",
                    0
                )
            )

        image = import_oca(input_path)
        Gimp.Display.new(image)

        return procedure.new_return_values(
            Gimp.PDBStatusType.SUCCESS,
            GLib.Error()
        )

    except Exception as exc:
        print("oca_load_run exception:", repr(exc))
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

        with tempfile.TemporaryDirectory() as temp_dir:
            content_json = build_content_json(image, temp_dir) if image is not None else {}

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
        return [PLUGIN_PROC, PLUGIN_PROC_LOAD]

    def do_set_i18n(self, name):
        return False

    def do_create_procedure(self, name):
        if name == PLUGIN_PROC:
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
                "Creates an .oca ZIP with layers as PNGs and a content.json manifest",
                name
            )
            procedure.set_attribution("Clifton Malecki", "Clifton Malecki", "2026")
            procedure.set_extensions("oca")
            procedure.set_mime_types("application/zip")
            procedure.set_menu_label("Open Cel Animation")
            return procedure

        elif name == PLUGIN_PROC_LOAD:
            procedure = Gimp.LoadProcedure.new(
                self,
                name,
                Gimp.PDBProcType.PLUGIN,
                oca_load_run,
                None,
                None
            )
            procedure.set_documentation(
                "Import OCA",
                "Imports an .oca ZIP file as a layered GIMP image",
                name
            )
            procedure.set_attribution("Clifton Malecki", "Clifton Malecki", "2026")
            procedure.set_extensions("oca")
            procedure.set_mime_types("application/zip")
            procedure.set_menu_label("Open Cel Animation")
            return procedure

        return None


Gimp.main(OcaSaver.__gtype__, sys.argv)