CREATE TABLE User
(
  user_id              INT unsigned NOT NULL AUTO_INCREMENT, 
  email            VARCHAR(150) NOT NULL,                
  biodata           VARCHAR(500),                
  username           VARCHAR(150) NOT NULL,
  user_photo        LONGBLOB, INDEX (user_photo(10)),
  password          VARCHAR(150) NOT NULL,
  UNIQUE (username),
  PRIMARY KEY(user_id)                     
);
CREATE TABLE Post
(
    post_id             INT unsigned NOT NULL AUTO_INCREMENT,
    post_Time         DATE NOT NULL,
    post_text         VARCHAR(500) NOT NULL,
    post_tag	 	INT unsigned NOT NULL,
    upvotes             INT unsigned NULL,
    downvotes           INT unsigned NULL,
    user_id              INT unsigned NOT NULL,
    post_photo          LONGBLOB, INDEX (post_photo(10)),
    translate           INT unsigned NOT NULL DEFAULT 0,
    PRIMARY KEY (post_id),
    FOREIGN KEY (user_id) REFERENCES User(user_id)
);

CREATE TABLE Following_list
(
  user_id              INT unsigned NOT NULL,
  following_id           INT unsigned NULL,
  username         VARCHAR (150) NULL,  
  email        VARCHAR (150)  NULL,   
  following_photo   LONGBLOB, INDEX (following_photo(10)),
  FOREIGN KEY (user_id) 	REFERENCES User(user_id)
 
);
CREATE TABLE Follower_list
(
  user_id              INT unsigned NOT NULL,
  follower_id           INT unsigned NULL,
    username         VARCHAR (150) NULL,  
  email        VARCHAR (150)  NULL, 
  follower_photo   LONGBLOB, INDEX (follower_photo(10)),
  FOREIGN KEY (user_id) REFERENCES User(user_id)
                    
);

CREATE TABLE Comment 
(
    user_id              INT unsigned NOT NULL,
    comment_id           INT unsigned NOT NULL AUTO_INCREMENT,
    post_id              INT unsigned NOT NULL,
    comment_Time         TIME NOT NULL,
    comment_text         VARCHAR(500) NOT NULL,
    user_photo             LONGBLOB, INDEX (user_photo(10)),
    PRIMARY KEY (comment_id),
    FOREIGN KEY (user_id) REFERENCES User(user_id),
    FOREIGN KEY (post_id) REFERENCES Post(post_id)
);
CREATE TABLE Upvote
(
    post_id             INT unsigned NOT NULL,
    user_id              INT unsigned NOT NULL,
    FOREIGN KEY (user_id) REFERENCES User(user_id),
    FOREIGN KEY (post_id) REFERENCES Post(post_id)
);
CREATE TABLE Downvote
(
    post_id             INT unsigned NOT NULL,
    user_id              INT unsigned NOT NULL,
    FOREIGN KEY (user_id) REFERENCES User(user_id),
    FOREIGN KEY (post_id) REFERENCES Post(post_id)
);
CREATE TABLE Saved
(
    post_id             INT unsigned NOT NULL,
    user_id              INT unsigned NOT NULL,
    username         VARCHAR (150) NULL,  
  email        VARCHAR (150)  NULL,
  saved_photo   LONGBLOB, INDEX (saved_photo(10)),
  saved_user_photo   LONGBLOB, INDEX (saved_user_photo(10)),
  text            VARCHAR(500) NULL,
    FOREIGN KEY (user_id) REFERENCES User(user_id),
    FOREIGN KEY (post_id) REFERENCES Post(post_id)
);