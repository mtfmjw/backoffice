-- login as backoffice to execute the following command
CREATE DATABASE backoffice OWNER backoffice;

-- createコマンドとは別transactionで実行する
GRANT ALL PRIVILEGES ON DATABASE backoffice TO backoffice;
ALTER SCHEMA public OWNER TO backoffice;
GRANT ALL ON SCHEMA public TO backoffice;
