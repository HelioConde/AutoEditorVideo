const fetch = require('node-fetch');
const request = require('request');
const fs = require('fs');
const express = require('express');
const { setTimeout } = require('timers/promises');

const app = express();
const port = process.env.PORT || 3011;

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.use(express.static('public'));

app.get('/', (req, res) => {
    res.sendfile('index.html');
});

app.post('/audioGerador', function (req, res) {
    let texto = req.body.texto;
    let titulo = req.body.titulo;
    let dir1 = './files/';
    let dir = './files/' + titulo + '/';
    let file = './files/' + titulo + '/' + titulo + '.mp3';
    console.log(texto)

    if (!fs.existsSync(dir1)) {
        //Efetua a criação do diretório
        fs.mkdirSync(dir1);
    }
    if (!fs.existsSync(dir)) {
        //Efetua a criação do diretório
        fs.mkdirSync(dir);
    }

    setTimeout(() => {
        fs.createWriteStream(file)
        let url = "https://text-to-speech-demo.ng.bluemix.net/api/v3/synthesize?text=" + encodeURI(texto) + "&voice=pt-BR_IsabelaV3Voice&download=true&accept=audio%2Fmp3";

        request.get(url).on('error', function (err) {
            // handle error
        }).pipe(
            fs.createWriteStream(file)
        );
        res.end("Enviado com sucesso");
    }, 500);
});

app.post('/imgGerador', function (req, res) {
    let url = req.body.texto;
    let titulo = req.body.titulo;
    let dir1 = './files/';
    let dir = './files/' + titulo + '/';
    let file = './files/' + titulo + '/' + titulo + '.mp3';
    console.log(dir);
    if (!fs.existsSync(dir1)) {
        //Efetua a criação do diretório
        fs.mkdirSync(dir1);
    }
    if (!fs.existsSync(dir)) {
        //Efetua a criação do diretório
        fs.mkdirSync(dir);
    }

    var download = function (uri, filename, callback) {
        request.head(uri, function (err, res, body) {
            console.log('content-type:', res.headers['content-type']);
            console.log('content-length:', res.headers['content-length']);

            request(uri).pipe(fs.createWriteStream(filename)).on('close', callback);
        });
    };
    let soma = 0;
    downloadSend();
    function downloadSend() {
        if (!fs.existsSync(dir + titulo + soma + '.png')) {
            download(url, dir + titulo + soma + '.png', function () {
                res.end('done');
            });
        } else {
            soma++;
            downloadSend();
        }
    }

});

app.listen(port, () => {
    console.log(`Example app listening on port ${port}`)
})