import unittest
from flask import Flask, request, render_template, redirect, url_for, session
import mysql.connector
import io
from io import BytesIO
from PIL import Image
import base64
import os
import datetime
from app import app

class FlaskTest(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
    
    def test_translate_with_username_in_session(self):
        with app.test_client() as client:
            with client.session_transaction() as session:
                session['username'] = 'testuser'

            response = client.get('/translate/1', follow_redirects=True)

            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/')

    def test_translate_without_username_in_session(self):
        with app.test_client() as client:
            with client.session_transaction() as session:
                session.clear()

            response = client.get('/translate/1', follow_redirects=True)

            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/')
    
    def test_untranslate_post(self):
        with app.test_client().session_transaction() as sess:
            sess['username'] = 'test_user'

        response = app.test_client().post('/untranslate/{}'.format(self.post_id))
        self.assertEqual(response.status_code, 302) # redirect

        with app.app_context():
            conn = app.config['db_connection']
            cursor = conn.cursor()
            cursor.execute("SELECT translate FROM Post WHERE post_id = %s", (self.post_id,))
            result = cursor.fetchone()
            self.assertEqual(result[0], 0)

            conn.rollback()
            cursor.close()
            conn.close()

    def test_register_with_valid_data(self):
        with app.test_client() as client:
            response = client.post('/register', data={
                'username': 'testuser',
                'email': 'testuser@example.com',
                'password': 'testpassword',
                'biodata': '',
                'confirm-password': 'testpassword'
            })
            self.assertEqual(response.status_code, 302)

    def test_register_with_invalid_password(self):
        with app.test_client() as c:
            response = c.post('/register', data={
                'username':'janedoe',
                'email':'janedoe@example.com',
                'password':'weak',
                'biodata':'My name is Jane Doe.',
                'confirm-password':'weak'
            })
            self.assertIn(b'register', response.data)
            self.assertEqual(response.status_code, 200)

    def test_register_with_existing_username(self):
        with app.test_client() as c:
            response = c.post('/register', data={
                'username':'janedoe',
                'email':'janedoe@example.com',
                'password':'securepassword',
                'biodata':'My name is Jane Doe.',
                'confirm-password':'securepassword'
          
            })
            self.assertEqual(response.status_code, 302)

            response = c.post('/register', data={
                'username':'janedoe',
                'email':'janedoe@example.com',
                'password':'securepassword',
                'confirm-password':'securepassword',
                'biodata':'My name is Jane Doe.'
            })
            self.assertIn(b'register', response.data)
            self.assertEqual(response.status_code, 302)
    
    def test_register_success(self):
        with app.test_client() as client:
            response = client.get('/register_success', follow_redirects=True)

            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Please log in', response.data)
            self.assertIn(b'Username', response.data)
            self.assertIn(b'Password', response.data)

    def test_index_with_username_in_session(self):
        with app.test_client() as client:
            with client.session_transaction() as session:
                session['username'] = 'testuser'

            response = client.get('/', follow_redirects=True)

            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/dashboard')

    def test_index_without_username_in_session(self):
        with app.test_client() as client:
            with client.session_transaction() as session:
                session.clear()

            response = client.get('/', follow_redirects=True)

            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/login')
            

    def test_login(self):
        with app.test_client() as client:
            # register a new user with a valid username and password
            response = client.post('/register', data={
                'username': 'testuser',
                'email': 'testuser@example.com',
                'password': 'testpassword',
                'biodata': '',
                'confirm-password': 'testpassword'
            })
            # check that the registration was successful and redirected to the success page
            assert response.status_code == 302
            # assert '/register_success' in response.headers['Location']

            # attempt to log in with correct username and password
            response = client.post('/login', data={
                'username': 'testuser',
                'password': 'testpassword'
            })

            # check that the login was successful and redirected to the dashboard page
            assert response.status_code == 302
            assert 'username' in session
            assert session['username'] == 'testuser'
            assert 'user_id' in session
            assert isinstance(session['user_id'], int)

            # attempt to log in with incorrect password
            response = client.post('/login', data={
                'username': 'testuser',
                'password': 'wrongpassword'
            })

            # check that the login failed and the error message is displayed
            assert response.status_code == 200
            assert b'Invalid username or password.' in response.data

            # attempt to log in with non-existent username
            response = client.post('/login', data={
                'username': 'nonexistentuser',
                'password': 'testpassword'
            })

            # check that the login failed and the error message is displayed
            assert response.status_code == 200
            assert b'Invalid username.' in response.data

    
    def test_dashboard_logged_in(self):
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['username'] = 'testuser'  # set a test username in the session

            response = client.get('/dashboard')
            self.assertEqual(response.status_code, 200)  # check if the response status code is 200
            self.assertTrue(b'testuser' in response.data)  # check if the username is present in the response

    def test_dashboard_not_logged_in(self):
        with app.test_client() as client:
            response = client.get('/dashboard')
            self.assertEqual(response.status_code, 302)  # check if the response status code is 302 (redirect)
            self.assertEqual(response.location, '/')  # check if the redirect location is the home page


    def test_add_post_with_valid_data(self):
        with app.test_client() as c:
            with c.session_transaction() as session:
                session['user_id'] = 1
                session['username'] = 'test_user'
                
            img = Image.new(mode='RGB', size=(50, 50), color=(255, 0, 0))
            img_io = io.BytesIO()
            img.save(img_io, format='JPEG')
            img_io.seek(0)
            encoded_img = base64.b64encode(img_io.getvalue()).decode('utf-8')
            
            data = {
                'post_term' : 0,
                'post_text': 'Test post text',
                'post_tag': 1,
                'image': (img_io, 'test.jpg')
            }
            
            response = c.post('/post/add', data=data, content_type='multipart/form-data')
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers['Location'], '/dashboard')
            
    def test_add_post_with_invalid_data(self):
        with app.test_client() as c:
            with c.session_transaction() as session:
                session['user_id'] = 1
                
            # missing post_text and post_tag fields
            data = {}
            
            response = c.post('/post/add', data=data, content_type='multipart/form-data')
            self.assertEqual(response.status_code, 400)

    def test_logout_with_authenticated_user(self):
        with app.test_client() as c:
            with c.session_transaction() as session:
                session['username'] = 'test_user'
                
            response = c.get('/logout1')
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers['Location'], '/login')
            
    def test_logout_with_unauthenticated_user(self):
        with app.test_client() as c:
            response = c.get('/logout')
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers['Location'], '/')

    def test_logout1(self):
        with app.test_client() as client:
            with client.session_transaction() as session:
                session['username'] = 'testuser'

            response = client.get('/logout1', follow_redirects=True)

            self.assertEqual(response.status_code, 200)
            self.assertIn(b'You have been logged out', response.data)
            self.assertNotIn(b'testuser', response.data)
            self.assertNotIn(b'Welcome back,', response.data)
        
    def test_profile_with_authenticated_user(self):
        with app.test_client() as c:
            with c.session_transaction() as session:
                session['username'] = 'Jyoti'
                
            response = c.get('/profile')
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.data)
            
    def test_profile_with_unauthenticated_user(self):
        response = app.test_client().get('/profile')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], '/')

    def test_other_profile_with_authenticated_user(self):
        with app.test_client() as c:
            with c.session_transaction() as session:
                session['username'] = 'Jyoti'
            response = c.get('/other_profile/new_username')
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.data)

    def test_other_profile_with_unauthenticated_user(self):
            response = app.test_client().get('/other_profile/test_user')
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers['Location'], '/')


    def test_other_profile_follower_with_authenticated_user(self):
        with app.test_client() as c:
            with c.session_transaction() as session:
                session['username'] = 'Jyoti'
                
            response = c.get('/other_profile_follower/new_username')
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.data)

    def test_other_profile_follower_with_unauthenticated_user(self):
            response = app.test_client().get('/other_profile_follower/test_user')
            self.assertEqual(response.status_code, 302)


    def test_other_profile_following_with_authenticated_user(self):
        with app.test_client() as c:
            with c.session_transaction() as session:
                session['username'] = 'new_username'
            
            response = c.get('/other_profile_following/Jyoti')
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.data)
            

    def test_other_profile_following_with_unauthenticated_user(self):
            response = app.test_client().get('/other_profile_following/test_user')
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers['Location'], '/')


    def test_update_profile(self):
        with app.test_client() as client:
            with client.session_transaction() as session:
                session['username'] = 'testuser'

            data = {'email': 'testuser@test.com',
                    'biodata': 'Test user',
                    'password': 'password123',
                    'username': 'newusername',
                    'image': (BytesIO(b'example image'), 'test.jpg')}

            response = client.post('/update_profile', data=data, follow_redirects=True)

            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Profile updated successfully', response.data)
            self.assertIn(b'newusername', response.data)
            self.assertIn(b'Test user', response.data)
            self.assertIn(b'testuser@test.com', response.data)

    def test_change_password_with_valid_credentials(self):
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess['username'] = 'testuser'
            response = c.post('/change_password', data={
                'current_password': 'oldpassword',
                'new_password': 'newpassword',
                'confirm_password': 'newpassword'
            })
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Password updated successfully.', response.data)

    def test_change_password_with_invalid_current_password(self):
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess['username'] = 'testuser'
            response = c.post('/change_password', data={
                'current_password': 'wrongpassword',
                'new_password': 'newpassword',
                'confirm_password': 'newpassword'
            })
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Invalid password. Please try again.', response.data)

    def test_change_password_with_mismatched_new_and_confirm_password(self):
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess['username'] = 'testuser'
            response = c.post('/change_password', data={
                'current_password': 'oldpassword',
                'new_password': 'newpassword',
                'confirm_password': 'mismatchedpassword'
            })
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'New password and confirm password do not match. Please try again.', response.data)

    def test_change_password_without_authentication(self):
        with app.test_client() as c:
            response = c.post('/change_password', data={
                'current_password': 'oldpassword',
                'new_password': 'newpassword',
                'confirm_password': 'newpassword'
            })
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/')

    def test_settings_logged_in(self):
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess['username'] = 'testuser'
            response = c.get('/settings')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Settings', response.data)
            self.assertIn(b'testuser', response.data)

    def test_settings_not_logged_in(self):
        with app.test_client() as c:
            response = c.get('/settings')
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/')
    
    def test_about_logged_in(self):
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess['username'] = 'testuser'
            response = c.get('/about')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'About Us', response.data)
            self.assertIn(b'testuser', response.data)

    def test_about_not_logged_in(self):
        with app.test_client() as c:
            response = c.get('/about')
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/')
    
    def test_delete_account(self):
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess['username'] = 'testuser'

            rv = c.get('/delete_account')
            self.assertEqual(rv.status_code, 200)

            # check that user has been deleted from the database
            conn = app.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM User WHERE username = %s', ('testuser',))
            data = cursor.fetchone()
            self.assertIsNone(data)
            cursor.close()
            conn.close()

            # check that session has been cleared
            with c.session_transaction() as sess:
                self.assertNotIn('username', sess)

    def test_delete_account_not_logged_in(self):
        with app.test_client() as c:
            rv = c.get('/delete_account')
            self.assertEqual(rv.status_code, 302)
            self.assertTrue(rv.location.endswith('/'))
    
    def test_saved_logged_in(self):
        with app.test_client() as c:
            with c.session_transaction() as session:
                session['username'] = 'test_user'
            response = c.get('/saved/1')
            self.assertEqual(response.status_code, 200)

    def test_saved_not_logged_in(self):
        with app.test_client() as c:
            response = c.get('/saved/1')
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.headers['Location'].endswith('/index'))
# saved post nhi banaya usme thodi bt aa rhi thi lets see coverage report cahnges or not.....
    def test_saved_post(self):
        # Test case for a logged in user
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['username'] = 'testuser'
            response = client.post('/saved_post/1')
            self.assertEqual(response.status_code, 302)  # expect redirect
            # assert that the data was correctly inserted into the Saved table
            # assuming a successful insert returns a redirect to the referrer
            self.assertEqual(response.headers['Location'], '/')  # expect index page
            
        # Test case for a non-logged in user
        with app.test_client() as client:
            response = client.post('/saved_post/1')
            self.assertEqual(response.status_code, 302)  # expect redirect
            self.assertEqual(response.headers['Location'], '/')  # expect index page
    
    def test_profile_follower(self):
        with app.test_client() as c:
            with c.session_transaction() as session:
                session['username'] = 'test_user'
            response = c.get('/profile_follower')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Profile Follower', response.data)
    
    def test_profile_following(self):
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess['username'] = 'test_user'
            response = c.post('/profile_following')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Following', response.data)
            self.assertIn(b'Followers', response.data)
    
    def test_following_other(self):
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess['username'] = 'test_user'

            response = c.post('/following_other/2')

            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/')
    
    def test_explore_tag(self):
        with app.test_client() as client:
            # Login as a test user
            with client.session_transaction() as session:
                session['username'] = 'test_user'
            
            # Call the explore_tag endpoint with a post tag of 1
            response = client.get('/explore/1')
            
            # Check that the response is successful
            self.assertEqual(response.status_code, 200)
            
            # Check that the rendered template contains the expected variables
            self.assertIn(b'post_tag = 1', response.data)
            self.assertIn(b'user', response.data)
            self.assertIn(b'posts', response.data)
            
            # Logout the test user
            with client.session_transaction() as session:
                session.pop('username', None)

    def test_explore(self):
        with app.test_client() as client:
            # Login as a test user
            with client.session_transaction() as session:
                session['username'] = 'test_user'
            
            # Call the explore endpoint
            response = client.get('/explore')
            
            # Check that the response is successful
            self.assertEqual(response.status_code, 200)
            
            # Check that the rendered template contains the expected variables
            self.assertIn(b'user', response.data)
            self.assertIn(b'posts', response.data)
            
            # Logout the test user
            with client.session_transaction() as session:
                session.pop('username', None)
    
    def test_view_comments(self):
        with app.test_client() as client:
            # Login as a test user
            with client.session_transaction() as session:
                session['username'] = 'test_user'
            
            # Call the view_comments endpoint with a valid post_id
            response = client.get('/comment/1')
            
            # Check that the response is successful
            self.assertEqual(response.status_code, 200)
            
            # Check that the rendered template contains the expected variables
            self.assertIn(b'comments', response.data)
            self.assertIn(b'post_id', response.data)
            self.assertIn(b'post', response.data)
            self.assertIn(b'user', response.data)
            self.assertIn(b'other_user', response.data)
            
            # Logout the test user
            with client.session_transaction() as session:
                session.pop('username', None)
    
    def test_add_comment(self):
        with app.test_client() as client:
            # Login with a test user
            with client.session_transaction() as sess:
                sess['username'] = 'testuser'

            # Insert a comment for post 1
            data = {'comment_text': 'Test comment for post 1'}
            response = client.post('/post/1/comments/add', data=data, follow_redirects=True)

            # Check that the comment was inserted in the database
            conn = app.config['DATABASE']
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM Comment WHERE comment_text = %s', ('Test comment for post 1',))
            comment = cursor.fetchone()
            self.assertIsNotNone(comment)

            # Check that the user ID matches the session user
            cursor.execute('SELECT * FROM User WHERE user_id = %s', (comment[3],))
            user = cursor.fetchone()
            self.assertEqual(user[1], 'testuser')

            cursor.close()
            conn.close()
    def test_comment():
        with app.test_client() as client:
        # simulate a logged-in user
            with client.session_transaction() as session:
                session['username'] = 'test_user'

            # make a GET request to the comment page for post_id = 1
            response = client.get('/comment/1')

            # assert that the response status code is 200 OK
            assert response.status_code == 200

            # assert that the response contains the post and user information
            assert b'<h2>Comment Section</h2>' in response.data
            assert b'This is a test post' in response.data
            assert b'Posted by test_user' in response.data
            with client.session_transaction() as session:
                del session['username']
            response = client.get('/comment/1')
            assert response.status_code == 302
            assert response.headers['Location'] == '/'

    def test_upvote_post_with_username_in_session(self):
        with app.test_client() as client:
            with client.session_transaction() as session:
                session['username'] = 'testuser'
                
            response = client.post('/upvote_post/1')
            
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers['Location'], '/')
            
    def test_upvote_post_without_username_in_session(self):
        with app.test_client() as client:
            response = client.post('/upvote_post/1')
            
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers['Location'], '/')
    
    def test_logged_in_user_can_downvote_post(self):
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess['username'] = 'testuser'

            response = c.post('/downvote_post/1')
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/')

    def test_non_logged_in_user_cannot_downvote_post(self):
        with app.test_client() as c:
            response = c.post('/downvote_post/1')
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/')
    
    def test_messages_with_session(self):
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess['username'] = 'testuser'
            response = c.get('/messages')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Messages', response.data)
    
    def test_messages_without_session(self):
        with app.test_client() as c:
            response = c.get('/messages')
            self.assertEqual(response.status_code, 302)
            self.assertRedirects(response, '/')
    
    def test_search_user_success(self):
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['username'] = 'test_user'
            response = client.post('/search', data={'sea': 'test'})
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'test_user', response.data)
            
    def test_search_user_no_query(self):
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['username'] = 'test_user'
            response = client.post('/search', data={'sea': ''})
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/dashboard')
            
    def test_search_user_no_session(self):
        with app.test_client() as client:
            response = client.post('/search', data={'sea': 'test'})
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/') 
if __name__ == '__main__':
    unittest.main()
