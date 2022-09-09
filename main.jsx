
var log = 0;
    var folder = new Folder("C:\\AutoEditor\\files");
    var folderFiles = myFolder.getFiles("");

    var folderSave = new Folder("C:\\AutoEditor\\save");
    var folderSaveFiles = folderSave.getFiles("");
    var name = "";

    for(obj in folderFiles){
        for(obj1 in folderSaveFiles){
            if (String(folderFiles[obj]).substr(20) + ".mp4" == String(folderSaveFiles[obj1]).substr(19)){
            } else {
                name = String(folderFiles[obj]).substr(20);
                teste(name);
            }
        }
    }


function teste(name){
    app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);
    app.newProject();
    app.beginUndoGroup("Import and rendering test");
    var myFolder = new Folder("C:\\AutoEditor\\files\\"+name);
    var myFolder2 = new Folder("C:\\AutoEditor\\video");
    var myImportOptions = new ImportOptions();
    var importedLayers = new Array();

    var myFiles = myFolder.getFiles("*.png");
    var myVideoFiles = myFolder2.getFiles("*.mp4");
    var myAudioFiles = myFolder.getFiles("*.mp3");
    var allMyFiles = myFiles.concat(myAudioFiles, myVideoFiles);

    var numFiles = allMyFiles.length;
    var numAudio = 0;
    var numVisual = 0;
    var numVideo = 0;
    var audioArray = new Array();
    var videoArray = new Array();
    var visualArray = new Array();
    
    for (var i = 0; i < allMyFiles.length; i++) {
        myImportOptions.file = allMyFiles[i];
        importedLayers.push(app.project.importFile(myImportOptions));
    }

    var duration = 0;
    
    for (var e = 1; e <= app.project.numItems; e++) {
        if (app.project.item(e).hasVideo == true) {
            numVideo++;
            videoArray.push(app.project.item(e));
        } else   if (app.project.item(e).hasAudio == true) {
            numAudio++;
            audioArray.push(app.project.item(e));
            duration += app.project.item(e).duration;
        } else {
        }
    }

$.writeln(duration);
    var tempComp = app.project.items.addComp(name, 1280, 720, 1, duration, 30);
    tempComp.openInViewer();
    var startTime = 0;
    var comp = app.project.activeItem;

    for (var q = 0; q < audioArray.length; q++) {
        var thisLayer = tempComp.layers.add(audioArray[q]);
        thisLayer.audioEnabled = true;
        thisLayer.startTime = 0;
        
    }

    for (var q = 0; q < videoArray.length; q++) {
        var thisLayer = tempComp.layers.add(videoArray[q]);
        thisLayer.audioEnabled = false;

        var myRect = thisLayer.sourceRectAtTime(0, false);
        var myScale = thisLayer.property("Scale").value;
        var myNewScale = myScale * Math.min (tempComp.width / myRect.width, tempComp.height / myRect.height);
        thisLayer.property("Scale").setValue(myNewScale);
        thisLayer.property("Position").setValue([tempComp.width / 2,tempComp.height / 2]);
    }

    var myFile = new File("C:\\AutoEditor\\save\\"+name+".mp4");
    var theRender = app.project.renderQueue.items.add(tempComp);

    theRender.outputModules[1].applyTemplate("AVI DV NTSC 48kHz");
    theRender.outputModules[1].file = myFile;
    app.endUndoGroup();
    //app.project.renderQueue.render();
    app.project.renderQueue.queueInAME(true);

    //app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);
    //app.newProject();
}