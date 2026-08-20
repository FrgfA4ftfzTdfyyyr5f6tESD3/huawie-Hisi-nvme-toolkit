from setuptools import setup, find_packages

setup(
    name="hisi-nve-py",
    version="3.0.0",
    description="Offline manager, parser, and bootloader unlocker for Huawei Kirin NVME partitions in pure Python",
    author="Open Source Contributors",
    license="GPL-3.0",
    packages=find_packages(),
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "hisi-nve=hisi_nve_cli:main",
            "hisi-nve-gui=hisi_nve_interactive:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Topic :: System :: Hardware",
        "Topic :: Utilities",
    ],
)
