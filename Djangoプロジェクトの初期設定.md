# Djangoプロジェクトの初期設定

Djangoプロジェクトを一から整備する場合に必要な手順のまとめ

## Python環境の初期設定

- Virtual Environmentのインストール

```batch
python -m venv .venv
```

- Virtual Environmentの起動
  
```batch
activate_venv.bat
```

- 必要なパッケージのインストール
  
```batch
pip install -r requirements.txt
```

## データベース環境の初期設定

- デフォルトのpostgresユーザーとしてDBにログインし、postgres/create_user.sqlをPgadmin4で実行してDBユーザーを作成する
- 新規作成したbackofficeユーザーとしてDBにログインし、postgres/create_database.sqlをPgadmin4で実行してbackoffice用データベースを作成する

## Django環境の初期設定

- .env_sampleを.envにコピーする（.envはGitリポジトリに保持しない）

## Dajngo固有テーブルの初期化

```batch
python manage.py migrate
```

## Django Suer Userの作成

```batch
set DJANGO_SUPERUSER_USERNAME=admin
set DJANGO_SUPERUSER_EMAIL=backoffice@leadingsoft.co.jp
set DJANGO_SUPERUSER_PASSWORD=P09olp09ol
python manage.py createsuperuser --noinput
```

## Django開発用サーバーの起動

```batch
python manage.py runserver
```
