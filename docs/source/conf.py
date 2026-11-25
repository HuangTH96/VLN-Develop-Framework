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

# -- 每次构建前自动重新生成 API 页面：新增模块无需手改 rst --
def run_apidoc(app):
    from sphinx.ext.apidoc import main as apidoc_main
    out_dir = os.path.join(DOCS_SOURCE, 'api')
    apidoc_main(['-f', '-e', '-M', '--private', '-o', out_dir, os.path.join(PROJECT_ROOT, 'spf')])

def setup(app):
    app.connect('builder-inited', run_apidoc)

# -- 构建 --
templates_path = ['_templates']
exclude_patterns = []
language = 'zh_CN'

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
