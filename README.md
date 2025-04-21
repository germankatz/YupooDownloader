<h1 style="text-align:center;">YupooDownloader</h1>

<p style="text-align:center;">This script downloads all albums from a Yupoo gallery into a dump folder, creating a subfolder for each album named after its title.</p>

---

## Setup

Ensure you have python 3.6+ installed.

```
pip install -r requirements.txt

```

### Configure details.json

In the array yupoos you can place an object with a structure like this:

```
{
    "productCount": "n",
    "yupoo_link": "https://namename.x.yupoo.com/categories/3484623"
}
```

It will download the first `n` albums in the same order as the yupoo category.

### Run the script

```
py YupooPhotoDownloader.py
```
