import pikepdf
import itertools
import sys

#パスワードがかけられているPDFファイル
pdf_lock = r""
#パスワード解除後のPDFファイル
pdf_nolock = r""

#パスワードの確認に使用する文字
characters = [ '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']

#パスワードの桁数の設定
count = 3

#総当たり開始
while True:
    count += 1
    for password in itertools.product(characters,repeat=count):
        try:
            #パスワードの文字を結合
            password = ''.join( password )

            pdf = pikepdf.open(pdf_lock, password=password)
            pdf_unlock = pikepdf.new()
            pdf_unlock.pages.extend(pdf.pages)
            pdf_unlock.save(pdf_nolock)
        except:
            print(password + ' は一致しませんでした')
        else:
            print('パスワードは' + password + 'でした。')
            #処理終了
            sys.exit()
