# pyMMAX2

This is the repository for pyMMAX2, a Python API for MMAX2. pyMMAX2 is introduced in <a href="https://github.com/nlpAThits/pyMMAX2/raw/main/LAW20_Final.pdf">this paper</a>, presented as a poster at <a href="https://sigann.github.io/LAW-XIV-2020/">LAW 2020</a>.

**Currently under construction, stay tuned!**

### Installation
Perform the following steps for a minimal installation. For actual applications, simply install pyMMAX2 and its required dependencies (if not installed already) into your working environment.

```
$ conda create --name pymmax2 python=3.6 colorama beautifulsoup4 regex jpype1
$ source activate pymmax2
$ pip install lxml
$ git clone https://github.com/nlpAThits/pyMMAX2.git
$ cd pyMMAX2
$ pip install .
```

If you want to use the JPype-based integration of the MMAX2 annotation scheme business logic (recommended), you need a current MMAX2 version, which can be downloaded from <a href="https://github.com/nlpAThits/MMAX2">here</a>.
MMAX2 does not require any installation, and comes with all necessary libraries. 
