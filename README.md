# For packaged files, see: https://ecse.rpi.edu/\~wiltk2/LITEC/Simulator/

### Running the project from source:
To run the gui from source you must have the following dependencies installed:
* numpy
* pygame>=2.0.0.dev6
* Pygments
* scipy
* matplotlib>=3.0.0

using a version of pygame < 2.0 will result in an error when running lab 4.

### Installation on Windows:
download the source code to the directory of your choosing
* install **python3** ( https://docs.python.org/3/using/windows.html ) 

* **Open command prompt** ( Windows Key + R > Type: "cmd" > presss enter)

**Ensure that pip is installed** by typing pip and pressing enter
~~~
pip --version
~~~

**Navigate to the install directory:**
~~~
cd C:\path\to\install\directory
~~~

**Install dependencies using pip:**
~~~
 pip install -r Requirements.txt
~~~
### Running the simulator
From the install directory:
~~~
cd Simulator && python LITECsimulator.py
~~~


### Installation on Linux:
* download the source code to the directory of your choosing
* install **python3** ( https://docs.python.org/3/using/unix.html#on-linux ) 

**In terminal:**
~~~
cd path/to/installation/directory/
pip install -r Requirements.txt
~~~
### Running the simulator
From the install directory:
~~~
cd Simulator && python LITECsimulator.py
~~~
