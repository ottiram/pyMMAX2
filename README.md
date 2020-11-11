# pyMMAX2

This is the repository for pyMMAX2, a Python API for MMAX2. pyMMAX2 is introduced in <a href="https://github.com/nlpAThits/pyMMAX2/raw/main/LAW20_Final.pdf">this paper</a>, presented as a poster at <a href="https://sigann.github.io/LAW-XIV-2020/">LAW 2020</a>.

**This site is currently under construction, stay tuned!**

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
Note that the `--common_paths` parameter is used to supply a global common_paths.xml file (not present in the original dataset).
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
The script just loads one .mmax file and prints some project info to the console. Since no MMAX2 libraries base folder is specified using the `--mmax2_libs` parameter, default attributes for the two markable levels **coref** and **sentences** are not available. 

Compare the above to the behaviour of the following command, which __does__ specify the MMAX2 libraries base folder, causing Java-based annotation scheme handling to be executed in the background. 
The effects are two-fold: 
First, info messages from the Java code are printed to the console.
Second, default attributes for both markable levels are determined from the annotation scheme xml files (as specified in global_common_paths.xml), and displayed with the project info.

```
$ python load_mmax.py \
   --mmax_file ../MMAX2-Showcase/acl_anthology_coref_coling_2012/C/C02-1016/C02-1016.mmax \
   --common_paths ../MMAX2-Showcase/acl_anthology_coref_coling_2012/common_files/global_common_paths.xml \
   --mmax2_libs ../MMAX2/Libs/

Reading <annotation> tags from common paths file ../MMAX2-Showcase/acl_anthology_coref_coling_2012/common_files/global_common_paths.xml
Loading level coref ... 
   Creating anno scheme
   Creating markable level
File header: <?xml version="1.0" encoding="UTF-8"?>
Loading level sentence ... 
   Creating anno scheme
   Creating markable level
File header: <?xml version="1.0" encoding="UTF-8"?>
Layer sentence has been set to visible!

MMAX2 Project Info:
-------------------
.mmax file        : ../MMAX2-Showcase/acl_anthology_coref_coling_2012/C/C02-1016/C02-1016.mmax
Basedata elements : 4222
Markable levels   :
 coref            : 267 markables [default: NP_Form:none, Coref_class:empty, Sure:yes]
 sentence         : 195 markables [default: imported_tag_type:]
```
