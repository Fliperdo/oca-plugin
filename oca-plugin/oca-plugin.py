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
from gi.repository import GObject


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

        # Warning - flattening removes alpha
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

        image = Gimp.Image.new(width, height, 0)
        # Note: image.set_name() not available in GIMP 3.2, name handled via filename

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

            # Use the first layer from the loaded image rather than flattening it,
            # to preserve any alpha channel / transparent pixels in the PNG.
            loaded_layers = loaded_image.get_layers()
            if not loaded_layers:
                print(f"Warning: no layers found in {frame_path}")
                loaded_image.delete()
                continue
            loaded_layer = loaded_layers[0]

            new_layer = Gimp.Layer.new_from_drawable(loaded_layer, image)
            new_layer.set_name(layer_name)
            new_layer.set_opacity(opacity)
            new_layer.set_visible(visible)

            image.insert_layer(new_layer, None, -1)
            new_layer.set_offsets(position[0], position[1])

            loaded_image.delete()
            print(f"Imported layer: {layer_name}")

        if image.get_layers():
            image.set_selected_layers([image.get_layers()[0]])

        print(f"Done! Imported {len(oca_layers)} layers from {input_path}")
        return image




# Consolidated plugin below — OcaLoader and OcaSaver removed to avoid duplication

class OcaPlugin(Gimp.PlugIn):
    """Main plugin that registers both load and save procedures."""
    def do_query_procedures(self):
        return [PLUGIN_PROC_LOAD, PLUGIN_PROC]

    def do_set_i18n(self, name):
        return False

    def do_create_procedure(self, name):
        if name == PLUGIN_PROC_LOAD:
            procedure = Gimp.LoadProcedure.new(
                self,
                name,
                Gimp.PDBProcType.PLUGIN,
                self.load_run,
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
        elif name == PLUGIN_PROC:
            procedure = Gimp.ExportProcedure.new(
                self,
                name,
                Gimp.PDBProcType.PLUGIN,
                False,
                self.save_run,
                None,
                None
            )
            procedure.set_documentation(
                "Export as OCA",
                "Creates an .oca ZIP with layers as PNGs and a content.json manifest",
                name
            )
            procedure.set_attribution("Clifton Malecki", "Clifton Malecki", "2026")
            procedure.set_menu_label("Open Cel Animation")
            procedure.set_extensions("oca")
            procedure.set_mime_types("application/zip")
            return procedure
        return None

    def load_run(self, procedure, run_mode, file, metadata, flags, config, *extra):
        path = file.get_path()
        image = import_oca(path)

        # Return status and the loaded image as per GIMP 3 plug-in API
        return Gimp.ValueArray.new_from_values([
            GObject.Value(Gimp.PDBStatusType, Gimp.PDBStatusType.SUCCESS),
            GObject.Value(Gimp.Image, image),
        ]), flags


    def save_run(self, procedure, run_mode, image, file, metadata, config, *extra):
        try:
            output_path = file.get_path()
            if not output_path.lower().endswith(".oca"):
                output_path += ".oca"

            with tempfile.TemporaryDirectory() as temp_dir:
                content_json = build_content_json(image, temp_dir)
                export_layers(image, temp_dir)

                with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr("content.json", json.dumps(content_json, indent=2) + "\n")
                    for filename in os.listdir(temp_dir):
                        filepath = os.path.join(temp_dir, filename)
                        zf.write(filepath, f"images/{filename}")
                        print(f"Zipped: images/{filename}")

            return procedure.new_return_values(
                Gimp.PDBStatusType.SUCCESS,
                None
            )
        except Exception as exc:
            print(f"OcaPlugin.save_run exception: {repr(exc)}")
            import traceback
            traceback.print_exc()
            error = GLib.Error.new_literal(
                GLib.quark_from_string("oca-plugin"),
                str(exc),
                0
            )
            return procedure.new_return_values(
                Gimp.PDBStatusType.EXECUTION_ERROR,
                error
            )

Gimp.main(OcaPlugin.__gtype__, sys.argv)