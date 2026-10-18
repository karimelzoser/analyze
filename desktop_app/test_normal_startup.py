"""Regression for the actual double-click launcher, not only --smoke-test.

This test specifically prevents the 2026-10-18 NameError where the normal
entry point referenced 'engineering_workspace' without importing it.
"""
from pathlib import Path
import ast


def test_production_main_guard_routes_via_shared_launcher():
    source=Path(__file__).with_name("app_modern_final.py").read_text(encoding="utf-8")
    tree=ast.parse(source)
    assert "def launch_desktop" in source
    assert "engineering_review_ui.EngineeringReviewApp()" in source
    assert "engineering_workspace.EngineeringWorkspaceApp().mainloop()" not in source
    launcher=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=="launch_desktop")
    called=[n for n in ast.walk(launcher) if isinstance(n,ast.Call)]
    assert any(isinstance(n.func,ast.Attribute) and n.func.attr=="mainloop" for n in called)


def test_real_mainloop_launcher_uses_instantiated_review_ui(monkeypatch):
    import app_modern_final

    calls=[]
    class DummyApp:
        def __init__(self):
            calls.append("constructed")
        def mainloop(self):
            calls.append("mainloop")

    monkeypatch.setattr(app_modern_final.engineering_review_ui,"EngineeringReviewApp",DummyApp)
    assert app_modern_final.launch_desktop()==0
    assert calls==["constructed","mainloop"]
