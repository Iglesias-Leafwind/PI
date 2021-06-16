How to run the app:

Step 1:
-Verify that you have installed:
->Python 3.8
-https://www.python.org/downloads/release/python-380/
->Java Developer Kit 11
-https://www.oracle.com/pt/java/technologies/javase-jdk11-downloads.html
->CMAKE
-https://cmake.org/download/

Step 2:
-Start you app by running imageable.exe

Known issues:
-Currently jdk works between 11 and 15
-Problems with neo4j or elasticsearch not finding JAVA?
->Setup JAVA_HOME as a environment variable:
-->Windows:
->Locate your Java installation directory (probably: C:\Program Files\Java\jdk11)
->Do one of the following:
>Windows 7 – Right click My Computer and select Properties > Advanced
>Windows 8 – Go to Control Panel > System > Advanced System Settings
>Windows 10 – Search for Environment Variables then select Edit the system environment variables
->Click the Environment Variables button.
->Under System Variables, click New.
->In the Variable Name field, enter:
>JAVA_HOME
->In the Variable Value field, enter your JDK installation path (probably: C:\Program Files\Java\jdk11)
->Click OK and Apply Changes as prompted

-->Linux:
->Open Console
->Make sure you have installed Java already
->Execute: vi ~/.bashrc OR vi ~/.bash_profile
->add line : export JAVA_HOME=/usr/java/jdk11
->save the file.
->source ~/.bashrc OR source ~/.bash_profile
->Execute : echo $JAVA_HOME
->Output should print the path /usr/java/jdk11
