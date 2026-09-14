"""Keep the original script/resource layout intact inside standalone wheels."""
from pathlib import Path
import shutil
from setuptools import setup
from setuptools.command.build_py import build_py

class BuildWithResources(build_py):
    def run(self):
        super().run()
        source = Path(__file__).resolve().parent
        for directory in ('scripts', 'skills', 'agents', 'hooks', 'templates', '.claude-plugin'):
            destination = Path(self.build_lib) / 'vibe_shield' / '_resources' / directory
            shutil.copytree(source / directory, destination, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))

setup(cmdclass={'build_py': BuildWithResources})
