# -*- coding: utf-8 -*-
"""快速编译检查"""
import py_compile, sys, os

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
files = [
    'app.py', 'database.py', 'data_import.py', 'analysis_engine.py', 'suggestions.py',
    'pages/overview.py', 'pages/member_analysis.py', 'pages/activity_analysis.py', 'pages/insights.py',
    'utils/stratification.py',
]
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print('OK:', f)
    except py_compile.PyCompileError as e:
        print('FAIL:', f, str(e))
