const { Client } = require('discord-rpc');
const fs = require('fs');
const chokidar = require('chokidar');

const clientId = '507982587416018945'; // Discord Developer Portal で作成したアプリのクライアントID
const rpc = new Client({ transport: 'ipc' });

rpc.login({ clientId }).catch(console.error);

rpc.on('ready', () => {
  console.log('RPC Connected');

  const nowPlayingFilePath = "E:\\music\\nowmusic.txt"; // 実際のファイルパスに置き換える
  let startTimestamp = 0; // 曲の開始時刻を保持する変数
  let endTimestamp = 0; // 曲の終了時刻を保持する変数

  // ファイルの更新を監視する
  const watcher = chokidar.watch(nowPlayingFilePath, {
    persistent: true,
  });

  watcher.on('change', (path) => {
    console.log(`File ${path} has been changed`);

    // 0.5秒後にアクティビティを更新する
    setTimeout(updateActivity, 500);
  });

  const updateActivity = () => {
    try {
      const data = fs.readFileSync(nowPlayingFilePath, 'utf8');

      console.log('Now playing data:', data);

      // ファイルが空の場合はRich Presenceをクリアする
      if (!data.trim()) {
        rpc.clearActivity();
        return;
      }

      const lines = data.split('\n');

      if (lines.length < 8) {
        console.error('Invalid data format in now playing file');
        return;
      }

      const title = lines[0].trim();
      const artist = lines[1].trim();
      const duration = lines[2].trim();
      const videolink = lines[3].trim();
      const channellink = lines[4].trim();
      const videoimage = lines[5].trim();
      const album = lines[6].trim();
      const playcount = lines[7].trim(); // playcountの行を追加
      
      // 曲の長さを秒に変換する
      const [minutes, seconds] = duration.split(':');
      const lengthSeconds = parseInt(minutes, 10) * 60 + parseInt(seconds, 10);

      startTimestamp = new Date();
      endTimestamp = startTimestamp.getTime() + (lengthSeconds * 1000);

      // ボタンの設定
      let buttons = [];

      // YouTube ボタン
      if (videolink && videolink !== '?') {
        buttons.push({ label: 'Play on YouTube', url: videolink });
      }

      // チャンネルリンク ボタン
      if (channellink && channellink !== '?') {
        buttons.push({ label: 'View Channel Link', url: channellink });
      }

      rpc.setActivity({
        details: title,
        state: album !== '?' ? `${artist} on ${album}` : artist, // albumが?でなければ結合する、そうでない場合はartistのみ表示
        startTimestamp: startTimestamp,
        endTimestamp: endTimestamp,
        largeImageKey: videoimage,
        largeImageText: `${playcount} count loop`,
        smallImageKey: 'small_image_key',
        smallImageText: 'Small Image Text',
        instance: true,
        buttons: buttons.length > 0 ? buttons : undefined,
      });
      

    } catch (err) {
      console.error('Error reading now playing file:', err);
    }
  };

  // 最初に1回更新する
  updateActivity();
});
