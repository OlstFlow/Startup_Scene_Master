import bpy
import os
import logging
import rna_keymap_ui

logging.basicConfig(level=logging.DEBUG)

bl_info = {
    "name": "Startup Scene Master",
    "author": "OLST & GPT",
    "version": (1, 3),
    "blender": (4, 3, 0),
    "location": "3D View > Sidebar > Scene Templates",
    "description": "Allows quick loading of custom scene templates.",
    "wiki_url": "",
    "category": "Scene",
}

selected_template = None
addon_keymaps = []

def get_template_files(self, context):
    preferences = context.preferences.addons[__name__].preferences
    template_directory = bpy.path.abspath(preferences.template_path)
    templates = []

    logging.debug(f"Checking directory: {template_directory}")

    if os.path.exists(template_directory):
        for file in os.listdir(template_directory):
            if file.endswith(".blend"):
                name = os.path.splitext(file)[0]
                templates.append((name, name, "", len(templates)))
                logging.debug(f"Found file: {name}")
    else:
        logging.warning(f"Template directory does not exist: {template_directory}")

    return templates

class StartupSceneMasterPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    template_path: bpy.props.StringProperty(
        name="Template Path",
        description="Path to the folder containing scene templates",
        default="",
        maxlen=1024,
        subtype='DIR_PATH'
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "template_path", text="Template Path")

        # Hotkey UI
        wm = context.window_manager
        kc = wm.keyconfigs.addon
        if kc:
            km = kc.keymaps.get('3D View')
            if km:
                for kmi in km.keymap_items:
                    if kmi.idname == "template.select":
                        rna_keymap_ui.draw_kmi([], kc, km, kmi, layout, 0)

class TEMPLATE_OT_select(bpy.types.Operator):
    bl_idname = "template.select"
    bl_label = "Select Scene Template"
    bl_description = "Select a scene template to load"

    choice: bpy.props.EnumProperty(
        name="Templates",
        description="Choose the desired scene template",
        items=get_template_files
    )

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        global selected_template

        preferences = context.preferences.addons[__name__].preferences
        template_directory = bpy.path.abspath(preferences.template_path)
        template_file = f"{self.choice}.blend"
        full_path = os.path.join(template_directory, template_file)

        if os.path.exists(full_path):
            if bpy.data.is_saved:
                bpy.ops.template.confirm('INVOKE_DEFAULT', choice=self.choice)
                return {'CANCELLED'}
            else:
                selected_template = self.choice
                bpy.ops.template.prompt_save('INVOKE_DEFAULT')
                return {'CANCELLED'}
        else:
            self.report({'ERROR'}, f"Template file {template_file} not found in {template_directory}")
            return {'CANCELLED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class TEMPLATE_OT_confirm(bpy.types.Operator):
    bl_idname = "template.confirm"
    bl_label = "Warning!"
    bl_description = "Confirm template load and overwrite current scene"

    choice: bpy.props.StringProperty()

    def execute(self, context):
        global selected_template

        preferences = context.preferences.addons[__name__].preferences
        template_directory = bpy.path.abspath(preferences.template_path)
        template_file = f"{self.choice}.blend"
        full_path = os.path.join(template_directory, template_file)

        selected_template = self.choice

        with open(full_path, 'rb') as src_file, open(bpy.data.filepath, 'wb') as dst_file:
            dst_file.write(src_file.read())

        bpy.ops.wm.open_mainfile(filepath=bpy.data.filepath)
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Current file will be overwritten!")
        layout.label(text="All unsaved data will be lost.")

class TEMPLATE_OT_prompt_save(bpy.types.Operator):
    bl_idname = "template.prompt_save"
    bl_label = "Save Current File"
    bl_description = "Prompt to save the current file before loading a template"

    def execute(self, context):
        global selected_template

        if selected_template:
            bpy.app.handlers.save_post.append(post_save_load_template)

        bpy.ops.wm.save_as_mainfile('INVOKE_DEFAULT')
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Please, save the file first.")

def post_save_load_template(dummy):
    global selected_template

    if not selected_template:
        return

    preferences = bpy.context.preferences.addons[__name__].preferences
    template_directory = bpy.path.abspath(preferences.template_path)
    template_file = f"{selected_template}.blend"
    full_path = os.path.join(template_directory, template_file)

    bpy.app.handlers.save_post.remove(post_save_load_template)

    with open(full_path, 'rb') as src_file, open(bpy.data.filepath, 'wb') as dst_file:
        dst_file.write(src_file.read())

    bpy.ops.wm.open_mainfile(filepath=bpy.data.filepath)

def register_keymaps():
    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
    kmi = km.keymap_items.new("template.select", type='F7', value='PRESS')
    addon_keymaps.append((km, kmi))

def unregister_keymaps():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

classes = [
    StartupSceneMasterPreferences,
    TEMPLATE_OT_select,
    TEMPLATE_OT_confirm,
    TEMPLATE_OT_prompt_save
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    register_keymaps()

def unregister():
    unregister_keymaps()
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
