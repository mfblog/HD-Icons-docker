from flask import Flask, render_template, request, jsonify, send_from_directory, make_response
import os
import subprocess
import time
import threading
from PIL import Image

app = Flask(__name__)

# 图标存放位置
ICONS_DIR = os.path.join(os.getcwd(), 'icons')

# 图标文件夹映射
IMAGE_FOLDERS = {
    'all': ['border-radius', 'circle', 'svg', 'upload'],  # 所有图标
    'border-radius': os.path.join(ICONS_DIR, 'HD-Icons', 'border-radius'),  # 圆角图标
    'circle': os.path.join(ICONS_DIR, 'HD-Icons', 'circle'),                # 圆形图标
    'svg': os.path.join(ICONS_DIR, 'HD-Icons', 'svg'),                      # 矢量图标
    'upload': os.path.join(ICONS_DIR, 'upload')                             # 自定义上传图标
}

# 设置静态文件路径
app.static_folder = 'static'

# 提供静态文件
@app.route('/static/<path:filename>')
def serve_static(filename):
    try:
        return send_from_directory(app.static_folder, filename)
    except FileNotFoundError:
        return "文件未找到", 404

# 提供 icons 文件夹中的静态文件
@app.route('/icons/<path:subpath>')
def serve_icons(subpath):
    response = make_response(send_from_directory(ICONS_DIR, subpath))
    # 设置缓存头，缓存时间为半年（15768000 秒）
    response.headers['Cache-Control'] = 'public, max-age=15768000'
    return response

# 生成缩略图
def generate_thumbnail(image_path, thumbnail_path, size=(128, 128)):
    try:
        with Image.open(image_path) as img:
            img.thumbnail(size)
            img.save(thumbnail_path)
        return True
    except Exception as e:
        print(f"生成缩略图时出错: {e}")
        return False

# 检查是否有更新
def check_for_updates():
    try:
        # 获取 all_proxy 环境变量
        proxy = os.getenv('all_proxy')
        if proxy:
            # 设置 git 的代理
            subprocess.run(['git', 'config', '--global', 'http.proxy', proxy])
            subprocess.run(['git', 'config', '--global', 'https.proxy', proxy])

        result = subprocess.run(['git', '-C', os.path.join(ICONS_DIR, 'HD-Icons'), 'pull'], capture_output=True, text=True)
        return 'Already up to date.' not in result.stdout
    except Exception as e:
        print(f"检查更新时出错: {e}")
        return False

# 自动检查更新的线程
def auto_check_updates():
    while True:
        if check_for_updates():
            print("检测到更新，图标库已更新。")
        time.sleep(86400)  # 每天检查一次

# 初始化图标库
def init_icons_repo():
    if not os.path.exists(ICONS_DIR):
        os.makedirs(ICONS_DIR)
    if not os.path.exists(os.path.join(ICONS_DIR, 'HD-Icons')):
        print("icons 文件夹为空，正在克隆 HD-Icons 仓库...")
        proxy = os.getenv('all_proxy')
        if proxy:
            # 使用代理进行 git clone
            subprocess.run(['git', 'config', '--global', 'http.proxy', proxy])
            subprocess.run(['git', 'config', '--global', 'https.proxy', proxy])
        subprocess.run(['git', 'clone', 'https://github.com/xushier/HD-Icons.git', os.path.join(ICONS_DIR, 'HD-Icons')])

    # 创建 upload 文件夹
    upload_dir = os.path.join(ICONS_DIR, 'upload')
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    # 初始化缩略图
    generate_thumbnails_for_all_images()

# 为所有图片生成缩略图
def generate_thumbnails_for_all_images():
    for image_type in IMAGE_FOLDERS['all']:
        image_dir = os.path.join(ICONS_DIR, 'HD-Icons', image_type) if image_type != 'upload' else os.path.join(ICONS_DIR, 'upload')
        thumbnail_dir = os.path.join(ICONS_DIR, 'thumbnails', image_type)

        # 如果文件夹不存在，跳过
        if not os.path.exists(image_dir):
            print(f"文件夹 {image_dir} 不存在，跳过生成缩略图。")
            continue

        # 创建缩略图文件夹
        if not os.path.exists(thumbnail_dir):
            os.makedirs(thumbnail_dir)

        # 生成缩略图
        for image_name in os.listdir(image_dir):
            # 不对 SVG 文件生成缩略图
            if image_name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff', '.ico', '.tif')):
                image_path = os.path.join(image_dir, image_name)
                thumbnail_path = os.path.join(thumbnail_dir, image_name)
                if not os.path.exists(thumbnail_path):
                    print(f"生成缩略图: {thumbnail_path}")
                    generate_thumbnail(image_path, thumbnail_path)

@app.route('/')
def index():
    # 检查缩略图是否生成完毕
    if not os.path.exists(os.path.join(ICONS_DIR, 'thumbnails')):
        return "正在生成缩略图，请稍后刷新页面..."
    return render_template('index.html')

@app.route('/images')
def get_images():
    image_type = request.args.get('type', 'all').lower()
    search_query = request.args.get('search', '').lower()

    if image_type == 'all':
        # 动态合并所有子文件夹中的图片
        images = []
        for subfolder in IMAGE_FOLDERS['all']:
            subfolder_path = os.path.join(ICONS_DIR, 'HD-Icons', subfolder) if subfolder != 'upload' else os.path.join(ICONS_DIR, 'upload')
            if os.path.exists(subfolder_path):
                images.extend([{"name": img, "type": subfolder} for img in os.listdir(subfolder_path) if img.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp', '.tiff', '.apng', '.ico', '.tif')) and search_query in img.lower()])
    else:
        # 读取指定文件夹中的图片
        folder = IMAGE_FOLDERS.get(image_type)
        if folder and os.path.exists(folder):
            images = [{"name": img, "type": image_type} for img in os.listdir(folder) if img.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp', '.tiff', '.apng', '.ico', '.tif')) and search_query in img.lower()]
        else:
            images = []
    return jsonify(images)

@app.route('/check-update', methods=['GET'])
def check_update():
    if check_for_updates():
        return jsonify({'status': '有更新'})
    else:
        return jsonify({'status': '无更新'})

@app.route('/delete-image', methods=['POST'])
def delete_image():
    data = request.json
    image_name = data['image_name']
    
    # 原始文件路径
    original_path = os.path.join(ICONS_DIR, 'upload', image_name)
    
    # 缩略图文件路径
    thumbnail_path = os.path.join(ICONS_DIR, 'thumbnails', 'upload', image_name)
    
    # 标记是否删除成功
    success = False
    
    # 删除原始文件
    if os.path.exists(original_path):
        try:
            os.remove(original_path)
            success = True
        except Exception as e:
            print(f"删除原始文件时出错: {e}")
            return jsonify({'status': 'error', 'message': '删除原始文件失败'})
    
    # 删除缩略图文件
    if os.path.exists(thumbnail_path):
        try:
            os.remove(thumbnail_path)
            success = True
        except Exception as e:
            print(f"删除缩略图文件时出错: {e}")
            return jsonify({'status': 'error', 'message': '删除缩略图文件失败'})
    
    # 如果没有任何文件被删除
    if not success:
        return jsonify({'status': 'error', 'message': '文件不存在'})
    
    return jsonify({'status': 'success'})

@app.route('/upload-image', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': '没有文件上传'})
    
    files = request.files.getlist('file')  # 获取所有文件
    if not files:
        return jsonify({'status': 'error', 'message': '没有选择文件'})
    
    upload_dir = os.path.join(ICONS_DIR, 'upload')
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    
    for file in files:
        if file.filename != '':
            file.save(os.path.join(upload_dir, file.filename))
    
    # 生成缩略图
    generate_thumbnails_for_all_images()
    
    return jsonify({'status': 'success', 'message': '文件上传成功'})

if __name__ == '__main__':
    # 初始化图标库
    init_icons_repo()

    # 启动自动检查更新线程
    update_thread = threading.Thread(target=auto_check_updates)
    update_thread.daemon = True
    update_thread.start()

    # 启动 Flask 应用
    app.run(host='0.0.0.0', port=50560)