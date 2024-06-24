# LABhub

# Basics of LABhub
This readme will lead you through basic logic of LABhub and will explain how to use main features.

Structure of data

**Logs/notes** in LABhub can be either divided to so called **projects** or could be created without any category. Project should follow some scientific goal (e.g. investigation of propagtion of spin waves through domain walls.).

Each project can be further divided to **sessions**. Idea behind sessions is to collect measurements which were conducted with specific goal inside project. Also we recomend to put to one sessions only measurements which were conducted not so far from each other (e.g. one week).

Project can also contain logs/notes which aren't part of any sessions, but we strongly encourage you to put as many logs as possible to sessions. Whole data strucutre of project and sessions is concluded on the following diagram.
![dataStructure](https://github.com/OndrejW/LABhub/assets/6682213/8253429d-8842-45a4-bc1b-62cd61ece186)

## Structure of log/note

**Idea** is for the reason why you conduct this measurement (e.g. find position of DW). In the **comment** you can write some special occasions or properties of the measurement (e.g. measueremtn takes aprox. 2 hours).

**Path** should contain path to the measured data.

If someone helps you with measurement you can add him/her as a **co-operator**. If you measure some **sample** (basicly every measurement expect setup characterization), you should add link on this sample from database. After you select sample, **structures** which are already on the sample become visible. You can either select one, left it empty (e.g. film measurements), or fill new one (it will be created during submiting of log). Same principle held also for **project** and **session**. After selecting project, sessions becames visible, but there is no possibility to create new session during submiting log.

Each setup has predefined **attributes** (e.g. laser power). After selecting correct setup, you can load them by clicking on Load attributes. Afterwars you can add more attributes or delet unwated ones, by clicking on the cross.

**Pictures** can be added by drag and drop, pasting from clipboard (after clicking on rectangle), or with use of browse (on mobile phone there is also possibility to take image with camera). Each picture can have a title.
![logStructure](https://github.com/OndrejW/LABhub/assets/6682213/e1ecb884-9c3b-4d90-90e6-4cdd2462a245)

## Sessions

In session view logs can be displayed eiter in ascending or descending order. In the top most log every information will be displayed, but in the next logs only informations which differs will be displayed. This feature is implemented to save space and to allow user to focus more on the important things during strategy loops.

If you use Add log to this session or Add note to this session, information from last log/note will be prefilled in to the form. This is useful, becaouse usually between individual measuremnts not very much parameters are changed.
