// google-auth.js
const fs = require('fs');
const readline = require('readline');
const { google } = require('googleapis');

// credentials.jsonを読み込む
const CREDENTIALS_PATH = './Calendar_credentials.json';
const TOKEN_PATH = './token.json';

// クレデンシャルファイルを読み込む
const credentials = JSON.parse(fs.readFileSync(CREDENTIALS_PATH));
const { client_secret, client_id, redirect_uris } = credentials.installed;

// OAuth2クライアントを設定
const oAuth2Client = new google.auth.OAuth2(client_id, client_secret, redirect_uris[0]);

// トークンを取得する関数
function getAccessToken() {
    const authUrl = oAuth2Client.generateAuthUrl({
    access_type: 'offline',
    scope: ['https://www.googleapis.com/auth/calendar.events'],
    });

    console.log('以下のURLにアクセスして認証コードを取得してください:');
    console.log(authUrl);

    const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    });

    rl.question('認証コードを入力してください: ', (code) => {
    rl.close();
    oAuth2Client.getToken(code, (err, token) => {
        if (err) return console.error('トークンの取得中にエラーが発生しました:', err);
        oAuth2Client.setCredentials(token);
        fs.writeFileSync(TOKEN_PATH, JSON.stringify(token));
        console.log('トークンが保存されました');
    });
    });
}

// トークンが存在するか確認し、存在しない場合は取得する
if (fs.existsSync(TOKEN_PATH)) {
    const token = fs.readFileSync(TOKEN_PATH);
    oAuth2Client.setCredentials(JSON.parse(token));
} else {
    getAccessToken();
}

module.exports = oAuth2Client;
