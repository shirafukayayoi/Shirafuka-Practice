const { google } = require('googleapis');
const auth = require('./GoogleAuth');
require('dotenv').config();

// Google Calendar APIのクライアントを取得
const calendar = google.calendar({ version: 'v3', auth });

// イベントの詳細を定義
const event = {
  summary: 'Google Calendar APIによるイベント',
  description: 'これはGoogle Calendar APIを使ったサンプルイベントです。',
  start: {
    dateTime: '2024-08-01T10:00:00Z',
    timeZone: 'Asia/Tokyo',
  },
  end: {
    dateTime: '2024-08-01T12:00:00Z',
    timeZone: 'Asia/Tokyo',
  },
};

// イベントをカレンダーに挿入
calendar.events.insert(   // 非同期に実行されたときに呼び出す、エラーオブジェクトの自動作成
  {
    calendarId: process.env.GOOGLECALENDAR_ID,
    resource: event,
  },
  (err, event) => {   // 引数の指定
    if (err) {  // もし、エラがー発生した場合
      console.log('イベントの作成中にエラーが発生しました: ' + err);
      return;
    }
    console.log('イベントが作成されました');
  }
);
