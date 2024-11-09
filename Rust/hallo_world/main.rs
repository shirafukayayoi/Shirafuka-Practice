fn main() {
    let x = 5; // 不変の変数
    let mut y = 10; // 可変の変数

    println!("xの値: {}", x);
    println!("yの値: {}", y);

    y = 15; // yは可変なので、再代入が可能
    println!("yの新しい値: {}", y);
}
