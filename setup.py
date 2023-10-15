from setuptools import setup

requirements = [
    "beautifulsoup4==4.12.2",
    "PyQt5==5.15.9",
    "requests",
]

setup(
    name="justgiving_totaliser",
    version="0.0.1",
    description="Totaliser for JustGiving pages",
    author="Tachibana Kanade",
    author_email="h0m54r@mastodon.social",
    url="https://github.com/homsar/justgiving_totaliser",
    packages=[
        "justgiving_totaliser",
        "justgiving_totaliser.images",
        "justgiving_totaliser.assets",
        "justgiving_totaliser.tests",
    ],
    package_data={
        "justgiving_totaliser.images": ["*.png"],
        "justgiving_totaliser.assets": ["*.mp3"],
    },
    entry_points={
        "console_scripts": [
            "JustGivingTotaliser=justgiving_totaliser.justgiving_totaliser:main"
        ]
    },
    install_requires=requirements,
    zip_safe=False,
    keywords="justgiving_totaliser",
    classifiers=[
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
    ],
)
