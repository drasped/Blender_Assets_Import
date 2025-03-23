bl_info = {
    "name": "资产导入工具",
    "author": "drasped",
    "version": (8, 0),
    "blender": (4, 4, 0),
    "location": "侧边栏 > 工具",
    "description": "自动识别文件/文件夹的资产导入工具",
    "warning": "",
    "category": "工具",
}

import bpy
import os

ASSET_TYPES = [
    ('brushes', "笔刷", 'BRUSH_DATA'),
    ('meshes', "网格", 'MESH_MONKEY'),
    ('materials', "材质", 'MATERIAL'),
    ('node_groups', "节点组", 'NODETREE'),
    ('textures', "纹理", 'TEXTURE'),
    ('actions', "动作", 'ACTION'),
    ('armatures', "骨架", 'ARMATURE_DATA'),
    ('cameras', "相机", 'CAMERA_DATA'),
    ('collections', "集合", 'OUTLINER_COLLECTION'),
    ('images', "图像", 'IMAGE_DATA'),
    ('lights', "灯光", 'LIGHT'),
    ('objects', "对象", 'OBJECT_DATA'),
    ('palettes', "调色板", 'COLOR'),
    ('scenes', "场景", 'SCENE_DATA'),
    ('texts', "文本", 'TEXT'),
    ('workspaces', "工作区", 'WORKSPACE'),
    ('worlds', "世界环境", 'WORLD'),
]

class AssetImportSettings(bpy.types.PropertyGroup):
    import_brushes: bpy.props.BoolProperty(name="笔刷", default=False)
    import_meshes: bpy.props.BoolProperty(name="网格", default=False)
    import_materials: bpy.props.BoolProperty(name="材质", default=False)
    import_node_groups: bpy.props.BoolProperty(name="节点组", default=False)
    import_textures: bpy.props.BoolProperty(name="纹理", default=False)
    import_actions: bpy.props.BoolProperty(name="动作", default=False)
    import_armatures: bpy.props.BoolProperty(name="骨架", default=False)
    import_cameras: bpy.props.BoolProperty(name="相机", default=False)
    import_collections: bpy.props.BoolProperty(name="集合", default=False)
    import_images: bpy.props.BoolProperty(name="图像", default=False)
    import_lights: bpy.props.BoolProperty(name="灯光", default=False)
    import_objects: bpy.props.BoolProperty(name="对象", default=False)
    import_palettes: bpy.props.BoolProperty(name="调色板", default=False)
    import_scenes: bpy.props.BoolProperty(name="场景", default=False)
    import_texts: bpy.props.BoolProperty(name="文本", default=False)
    import_workspaces: bpy.props.BoolProperty(name="工作区", default=False)
    import_worlds: bpy.props.BoolProperty(name="世界环境", default=False)
    
    import_marked_only: bpy.props.BoolProperty(
        name="仅限标记资产",
        default=False
    )

class ASSET_OT_batch_import(bpy.types.Operator):
    bl_idname = "asset.batch_import"
    bl_label = "智能导入资产"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(subtype='FILE_PATH')

    def get_selected_types(self, context):
        settings = context.window_manager.asset_import_settings
        return [t[0] for t in ASSET_TYPES if getattr(settings, f"import_{t[0]}")]

    def execute(self, context):
        settings = context.window_manager.asset_import_settings
        selected_types = self.get_selected_types(context)
        
        if not selected_types:
            self.report({'ERROR'}, "请至少选择一个资产类型")
            return {'CANCELLED'}

        path = bpy.path.abspath(self.filepath)
        blend_files = []
        base_dir = ""

        # 自动识别路径类型
        if os.path.isdir(path):
            base_dir = path
            blend_files = [f for f in os.listdir(path) if f.endswith(".blend")]
            if not blend_files:
                self.report({'ERROR'}, "文件夹中没有.blend文件")
                return {'CANCELLED'}
        elif os.path.isfile(path) and path.endswith(".blend"):
            base_dir = os.path.dirname(path)
            blend_files = [os.path.basename(path)]
        else:
            self.report({'ERROR'}, "无效路径，请选择文件或文件夹")
            return {'CANCELLED'}

        import_stats = {t[0]:0 for t in ASSET_TYPES}

        for file_name in blend_files:
            file_path = os.path.join(base_dir, file_name)
            try:
                with bpy.data.libraries.load(file_path, link=False, assets_only=settings.import_marked_only) as (data_from, data_to):
                    # 处理工作区
                    if 'workspaces' in selected_types and hasattr(data_from, 'workspaces'):
                        for ws in data_from.workspaces:
                            try:
                                bpy.ops.workspace.append_activate(
                                    idname=ws,
                                    filepath=file_path
                                )
                                import_stats['workspaces'] += 1
                            except:
                                bpy.ops.workspace.append_activate(
                                    workspace=ws,
                                    filepath=file_path
                                )
                                import_stats['workspaces'] += 1
                                
                    # 处理其他资产
                    for asset_type in selected_types:
                        if asset_type == 'workspaces':
                            continue
                            
                        src_data = getattr(data_from, asset_type, [])
                        if src_data:
                            getattr(data_to, asset_type).extend(src_data)
                            import_stats[asset_type] += len(src_data)
                            
            except Exception as e:
                self.report({'WARNING'}, f"加载失败 {file_name}: {str(e)}")
                continue

        mode = "文件夹" if os.path.isdir(path) else "文件"
        report_msg = f"导入完成（{mode}模式）:\n"
        for asset_type, count in import_stats.items():
            if count > 0:
                type_name = next(t[1] for t in ASSET_TYPES if t[0] == asset_type)
                report_msg += f"• {type_name}: {count}个\n"
        
        self.report({'INFO'}, report_msg if any(import_stats.values()) else "未找到可导入资产")
        return {'FINISHED'}

    def invoke(self, context, event):
        # 简化后的文件选择器调用
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class ASSET_PT_import_panel(bpy.types.Panel):
    bl_label = "智能资产导入"
    bl_idname = "ASSET_PT_import_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = '工具'

    def draw(self, context):
        settings = context.window_manager.asset_import_settings
        layout = self.layout
        
        # 资产类型选择
        box = layout.box()
        box.label(text="资产类型选择:", icon='FILTER')
        grid = box.grid_flow(row_major=True, columns=2, align=True)
        for asset_id, asset_name, asset_icon in ASSET_TYPES:
            grid.prop(settings, f"import_{asset_id}", 
                     text=asset_name, 
                     icon=asset_icon,
                     toggle=True)
        
        # 过滤选项
        layout.separator()
        box = layout.box()
        box.prop(settings, "import_marked_only",
                text="仅导入标记资产",
                icon='BOOKMARKS',
                toggle=True)
        
        # 操作按钮
        layout.separator()
        layout.operator("asset.batch_import", 
                       icon='IMPORT', 
                       text="选择文件/文件夹")
        
        # 状态提示
        layout.separator()
        box = layout.box()
        box.label(text="操作说明:", icon='INFO')
        box.label(text="1. 选择资产类型")
        box.label(text="2. 点击按钮选择文件或文件夹")
        box.label(text="3. 自动识别路径类型执行导入")

def register():
    bpy.utils.register_class(AssetImportSettings)
    bpy.utils.register_class(ASSET_OT_batch_import)
    bpy.utils.register_class(ASSET_PT_import_panel)
    bpy.types.WindowManager.asset_import_settings = bpy.props.PointerProperty(
        type=AssetImportSettings
    )

def unregister():
    del bpy.types.WindowManager.asset_import_settings
    bpy.utils.unregister_class(ASSET_PT_import_panel)
    bpy.utils.unregister_class(ASSET_OT_batch_import)
    bpy.utils.unregister_class(AssetImportSettings)

if __name__ == "__main__":
    register()