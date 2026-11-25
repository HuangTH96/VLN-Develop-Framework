# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'VLN Develop Framework'
copyright = '2026, Huang Tianhao'
author = 'Huang Tianhao'
release = '1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

import os 
import sys

# 项目根目录
cur_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(cur_dir, '..','..'))
sys.path.insert(0, project_root)

import sys
import spf.base.command
sys.modules['command'] = spf.base.command

# 启动自动解析、Goolge文档风格支持、源码查看以及自动类型提示
extensions = [
    'sphinx.ext.autodoc',       # 核心：自动从代码提取文档
    'sphinx.ext.napoleon',      # 支持解析 Goolgle/NumPy 风格的注释
    'sphinx.ext.viewcode',      # 在文档中显示 [source] 源码连接
    'sphinx_autodoc_typehints', # 自动将代码中的type hints 融进文档
]

# 配置显示风格
autodoc_typehints = 'description'

templates_path = ['_templates']
exclude_patterns = []

language = 'zh_CN'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# html_theme = 'alabaster'
html_theme = 'sphinx_rtd_theme' # AirSim 同款 Read the Docs 主题
html_static_path = ['_static']
