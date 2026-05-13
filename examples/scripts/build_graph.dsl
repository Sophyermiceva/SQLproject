LOAD users;
LOAD orders;
LOAD products;

NODE User KEY user_id NAME name FROM users;
NODE Product KEY id NAME name FROM products;

EDGE Bought
    FROM orders
    SOURCE user_id
    TARGET product_id
    WEIGHT amount
    WHERE (amount >= 2) AND (amount <= 5);
