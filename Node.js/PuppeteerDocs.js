const puppeteer = require('puppeteer');

(async () => {
  // ブラウザを起動
  const browser = await puppeteer.launch();   //これは絶対必要
    
  // 新しいページを作成
  const page = await browser.newPage();   //これは絶対必要
    
  // 指定したページに移動
    await page.goto('https://example.com');
    
  // スクリーンショットを撮る（大きさ指定）
    await page.screenshot({
    path: 'example.png',
    clip: {
      x: 0,    // スクリーンショットの始点（x座標）
      y: 0,    // スクリーンショットの始点（y座標）
      width: 800,  // 幅
      height: 600  // 高さ
    }
    });

  // PDFを作成
    await page.pdf({ path: 'example.pdf', format: 'A4' });
    
  // ブラウザを閉じる
    await browser.close();
})();
