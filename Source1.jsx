app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);
app.newProject();
app.beginUndoGroup("Import and rendering test");
//var myFolder = new Folder("~\\Desktop\\editor");

var myFolder = new Folder("D:\\Meus projetos\\AutoEditor\\Gigante de Ferro");
var myFiles = myFolder.getFiles("*.png");
$.writeln(myFiles);