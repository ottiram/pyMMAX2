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
MMAX2 itself does not require any installation, and comes with all necessary libraries. 

### Loading and Validating MMAX2 datasets
The following example uses the streamlined version of the ACL Anthology coref dataset (original available <a href="https://www.aclweb.org/anthology/C12-2103/">here</a>) from the <a href="https://github.com/nlpAThits/MMAX2-Showcase">MMAX2-Showcase</a> project. 
Note that the `--common_paths` parameter is used to supply a **global** common_paths.xml file (not present in the original dataset). This is the recommended practice for large collections of homogeneous MMAX2 datasets, because it renders unnecessary the large number of identical style, scheme, customization, and common_paths files, allowing modifications in one place for the entire collection.
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

Compare the above to the behaviour of the following command, which *does* specify the MMAX2 libraries base folder, causing Java-based annotation scheme handling to be executed in the background. 
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
 coref            : 267 markables [default: <>NP_Form:none, Sure:yes]
 sentence         : 195 markables [default: imported_tag_type:]
```
Note that the coref_scheme.xml in the <a href="https://github.com/nlpAThits/MMAX2-Showcase">MMAX2-Showcase</a> version of the ACL Anthology dataset has been modified compared to the original scheme file, by making the **coref_class** attribute *dependent* on the **np_form** attribute having a non-default value.
This makes **np_form** a (in MMAX2 parlance) _branching_ attribute, which is visible in the `<>` prefix to the **np_form** attribute name above.

The main purpose of using the Java-based annotation scheme handling in pyMMAX2 is to support **validation**.
Validation is implemented on the level of individual markables, upon setting a markable's attributes with the `set_attributes()` method. 
As a general rule, attributes will **always be assigned** to the markable, **regardless of their being valid**. 
If validation errors are found, an **InvalidMMAX2AttributeException** will be raised. It is the developer's responsibility to handle this exception.

In the example above, validation was performed, but no exceptions were raised. The following example provokes validation errors by using a modified coref_schene.xml (via global_common_paths_with_errors.xml).

```
$ python load_mmax.py \
   --mmax_file ../MMAX2-Showcase/acl_anthology_coref_coling_2012/C/C02-1016/C02-1016.mmax \
   --common_paths ../MMAX2-Showcase/acl_anthology_coref_coling_2012/common_files/global_common_paths_with_errors.xml \
   --mmax2_libs ../MMAX2/Libs/

Reading <annotation> tags from common paths file ../MMAX2-Showcase/acl_anthology_coref_coling_2012/common_files/global_common_paths_with_errors.xml
Loading level coref ... 
   Creating anno scheme
   Creating markable level
File header: <?xml version="1.0" encoding="UTF-8"?>
Loading level sentence ... 
   Creating anno scheme
   Creating markable level
File header: <?xml version="1.0" encoding="UTF-8"?>
Layer sentence has been set to visible!
Error: Value ne not found on attribute NP_Form!

<SNIP>

Error: Value ne not found on attribute NP_Form!
53 validation exceptions, e.g.
Level: coref, ID: markable_168
Supplied: {'coref_class': 'set_110', 'sure': 'yes', 'np_form': 'ne'}
Valid:    {'sure': 'yes'}
Invalid:  {'coref_class': 'set_110', 'np_form': 'ne'}
Missing:  {}

MMAX2 Project Info:
-------------------
.mmax file        : ../MMAX2-Showcase/acl_anthology_coref_coling_2012/C/C02-1016/C02-1016.mmax
Basedata elements : 4222
Markable levels   :
 coref            : 267 markables [default: <>NP_Form:none, Sure:yes]
 sentence         : 195 markables [default: imported_tag_type:]
```
The error in the coref_scheme.xml used above consists of changing the allowed value 'ne' for the np_form attribute to 'none'. 
As a result, loading markables with the (now invalid) 'ne' value will raise a validation exception on every markable with 'np_form=ne'.
Single exceptions are collected during bulk markable loading, and another exception is raised at the end.
The above output is the result of handling this exception. 
Note that both 'np_form=ne' and 'coref_class=set_110' are treated as invalid, because the latter attribute is only valid if the former has a valid value.
