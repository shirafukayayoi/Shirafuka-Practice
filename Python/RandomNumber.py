import random


# 数あてゲームの作成
def number_game():
    # 乱数の生成
    answer = random.randint(1, 100)
    print("1から100までの数を当ててください")

    count = 0  # ユーザーが数を当てるまでの回数をカウントする変数

    # ユーザーが数を当てるまで繰り返す
    while True:
        guess = int(input("数を入力してください: "))  # intにして数字以外はエラー
        count += 1
        if guess == answer:  # ユーザーからの入力が正解と一致した場合
            print(f"正解です！{count}回目で当たりました！")
            break  # ループを抜ける
        elif guess < answer:
            print("もっと大きいです")
        else:  # elseを使うことで、小さいときを指定
            print("もっと小さいです")


# number_game()を呼び出す
number_game()

# 数をあてたらユーザーがクリックするまで表示されるようにする
input("終了するにはEnterキーを押してください")
