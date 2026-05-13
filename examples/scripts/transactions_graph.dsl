LOAD accounts;
LOAD transactions;

NODE Account KEY account_id FROM accounts;

EDGE Transfer
    FROM transactions
    SOURCE sender_id
    TARGET receiver_id
    WEIGHT amount
    WHERE (settled_flag > 0) AND (amount > 0);
