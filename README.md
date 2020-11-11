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

The following example uses the streamlined version of the ACL Anthology coref dataset (original available <a href="https://www.aclweb.org/anthology/C12-2103/">here</a>) from the <a href="https://github.com/nlpAThits/MMAX2-Showcase">MMAX2-Showcase</a> project.
```
$ python load_mmax.py \
      --mmax_file ../MMAX2-Showcase/acl_anthology_coref_coling_2012/C/C02-1016/C02-1016.mmax \
      --common_paths ../MMAX2-Showcase/acl_anthology_coref_coling_2012/common_files/global_common_paths.xml 
         
MMAX2 Project Info:
-------------------
.mmax file        : ../MMAX2-Showcase/acl_anthology_coref_coling_2012/C/C02-1016/C02-1016.mmax
Basedata elements : 4222
Markable levels   :
 coref            : 267 markables [default: Annotation scheme instance not available!]
 sentence         : 195 markables [default: Annotation scheme instance not available!]
```
