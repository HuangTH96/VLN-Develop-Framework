import os
import sys

# -- 项目信息 --
project = 'VLN Develop Framework'
copyright = '2026, Huang Tianhao'
author = 'Huang Tianhao'
release = '1.0'

# -- 路径：docs/source/conf.py -> 项目根目录(spf包所在目录) --
DOCS_SOURCE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(DOCS_SOURCE, '..','..'))
PACKAGE = 'spf'     # 要生成文档的包名
sys.path.insert(0, PROJECT_ROOT)

# -- 扩展 --
extensions = [
    'sphinx.ext.autodoc',       # 从代码提取文档
    'sphinx.ext.napoleon',      # Goolgle 风格的注释
    'sphinx.ext.viewcode',      # 在文档中显示 [source] 源码连接
    'sphinx_autodoc_typehints', # 把类型注解写进参数说明
]

# -- autodoc --
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
    'private-members': True,        # 抽象钩子（_get_platform_client 等）
    'exclude-members': '_abc_impl'  # ABC 内部属性，没有文档价值
}
autodoc_member_order = 'bysource'   # 按源码顺序
# 文档构建环境里不一定装了这些库：mock 掉，避免 "failed to import" 导致整页内容丢失
autodoc_mock_imports = ['airsim', 'msgpackrpc', 'cv2', 'rospy', 'cv_bridge', 'geometry_msgs', 'nav_msgs',
                        'sensor_msgs', 'djitellopy', 'yaml']

# -- napoleon / typehints（类型只在 sphinx_autodoc_typehints 里写一遍，避免重复）--
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_use_param = True
napoleon_use_ivar = True
typehints_use_rtype = False

def run_apidoc(app):
    """每次构建前重新生成 API 页面（Sphinx < 8.2 的做法）。

    app 是 Sphinx 应用对象：Sphinx 触发 ``builder-inited`` 事件时，把它作为第一个参数传给这里的函数
    （见下面 setup() 里的 app.connect）。这里用它的 srcdir 找到源码目录。

    调用的是 sphinx-apidoc 命令行，不依赖内部函数。先生成到临时目录，再同步到 source/api：
    内容没变的文件不动（保留修改时间，增量构建才有意义），对应模块已被删除或改名的旧页面会被清掉。
    只会删除 spf.*.rst 和 modules.rst，不会碰手写的页面。

    Sphinx >= 8.2 可以改用官方扩展，不再需要这个函数和 setup()：
        extensions += ['sphinx.ext.apidoc']
        apidoc_modules = [{'path': '../../spf', 'destination': 'api/', 'separate_modules': True,
                           'include_private': True, 'module_first': True}]
    """
    import filecmp
    import shutil
    import subprocess
    import tempfile

    pkg_dir = os.path.join(PROJECT_ROOT, PACKAGE)
    if not os.path.isdir(pkg_dir):
        raise RuntimeError(f'apidoc: 找不到包目录 {pkg_dir}，请检查 conf.py 里的 PROJECT_ROOT / PACKAGE')
    out_dir = os.path.join(app.srcdir, 'api')
    os.makedirs(out_dir, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([sys.executable, '-m', 'sphinx.ext.apidoc', '-f', '-e', '-M', '--private', '-q',
                        '-o', tmp, pkg_dir], check=True)
        fresh = set(os.listdir(tmp))
        for name in os.listdir(out_dir):
            generated = name == 'modules.rst' or name.startswith(PACKAGE + '.')
            if name.endswith('.rst') and generated and name not in fresh:
                os.remove(os.path.join(out_dir, name))
        for name in fresh:
            src, dst = os.path.join(tmp, name), os.path.join(out_dir, name)
            if not os.path.exists(dst) or not filecmp.cmp(src, dst, shallow=False):
                shutil.copyfile(src, dst)

def setup(app):
    app.connect('builder-inited', run_apidoc)

# -- 构建 --
templates_path = ['_templates']
exclude_patterns = []
language = 'zh_CN'

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
