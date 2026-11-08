# User Acceptance Test (UAT) script

**Project:** Online Bookstore (Team 2) · **Version:** 1.0 · **Prepared:** 5 November 2026

This is the manual acceptance test for the finished product, following the suites named in SRS section 6: authentication, catalog and search, cart and checkout, order management, payments, security and accessibility. The Test Plan names the Product Owner as the person who signs off the results.

Fill in the **Result** column with Pass or Fail for each scenario, and write down anything odd in **Notes**.

## Before you start

1. Start the whole project from the repository folder: `docker compose up --build`, then open <http://localhost:8000>.
2. Create an admin account: `docker compose exec web python manage.py createsuperuser`.
3. Create the demo coupon: `docker compose exec web python manage.py shell -c "from orders.models import Coupon; Coupon.objects.get_or_create(code='WELCOME10', defaults={'discount_percent': 10, 'is_active': True})"`.
4. Create a seller account: register a user on the site and verify it (scenarios U-01 and U-02), then run `docker compose exec web python manage.py make_seller <that username> --claim-unowned-books`.
5. Payments need Razorpay **test-mode** keys in your `.env` (`RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`). See `docs/SETUP.md`.
6. Keep a second terminal open with `docker compose logs -f worker`. Emails and SMS messages appear there.

## Scenarios

| ID | Role | Scenario | Steps | Expected result | Requirement | Result | Notes |
|---|---|---|---|---|---|---|---|
| U-01 | Buyer | Register | Open Register. Enter a username, email and a strong password twice. Submit. | The page says to check your email. The verification email with a link appears in the worker log. | BOOK-F-001 | | |
| U-02 | Buyer | Verify and log in | Open the link from the worker log. Then log in on the Log in page. | The link shows "Email verified". Login succeeds and the navigation shows "Log out (username)". | BOOK-F-001, 002 | | |
| U-03 | Buyer | Account lockout | Log out. Enter a wrong password 5 times, then the right one. | After 5 failures the account is reported as locked, and the right password is also refused. | BOOK-F-003 | | |
| U-04 | Admin | Unlock account | In `/admin/`, open Users, select the locked user and run "Unlock selected accounts". | The user can log in again. The action appears in the Admin action log. | BOOK-F-003, SR-005 | | |
| U-05 | Visitor | Browse the catalog | Open the home page. Go to page 2. | Books appear with covers, 20 per page, and page 2 shows the rest. | BOOK-F-010 | | |
| U-06 | Visitor | Search | Search for `orwell`. Then search for an ISBN. | Only matching books are listed. | BOOK-F-011 | | |
| U-07 | Visitor | Filter and sort | Choose a genre, set a price range, and sort by price low to high. | The list matches the filters and is in the right order. | BOOK-F-011 | | |
| U-08 | Visitor | Book page | Click a book title. | The page shows the cover, author, price, stock, description and the rating summary. | BOOK-F-010, 060 | | |
| U-09 | Buyer | Add to cart | While logged out, click Add to cart. Log in. Add 2 copies of a book. Open Cart. | Logged out, you are sent to log in and brought back. The cart shows 2 copies and the right subtotal. | BOOK-F-020 to 023 | | |
| U-10 | Buyer | Edit the cart | Change a quantity, remove an item, log out and log in again. | Totals update. The cart is still there after logging back in. A quantity above the stock is refused with a message. | BOOK-F-020 to 023 | | |
| U-11 | Buyer | Wishlist | On a book page click "Save for later". Open Wishlist. Click "Add to cart", then "Remove". | The button changes to "Saved". The book appears on the wishlist page. It can be added to the cart and removed, and the empty message shows afterwards. | BOOK-F-020 to 023 | | |
| U-12 | Buyer | Checkout with a coupon | Proceed to checkout. Add an address with a phone number. Enter `WELCOME10`. Place the order. | The order is created with a total 10% lower than the subtotal, and the payment window opens. | BOOK-F-030 to 035 | | |
| U-13 | Buyer | Pay in test mode | In the payment window choose Card. Use the test card 4111 1111 1111 1111 with any future expiry date and any CVV. On the mock bank page choose Success. (UPI test ID: `success@razorpay`.) | The payment succeeds and the order moves to PAID. No real money moves. | BOOK-F-030 to 035, SR-003 | | |
| U-14 | Buyer | Notifications | After U-12, look at the worker log. | An order confirmation email and an SMS line (`SMS to +91...`) appear. | SRS 2.2 | | |
| U-15 | Buyer | Confirmation and invoice | While logged in as the buyer, open `/api/orders/<order number>/confirmation` and `/api/orders/<order number>/invoice` in the browser. | The confirmation and the invoice show the items, prices and total of the order. | BOOK-F-030 to 035 | | |
| U-16 | Buyer | Order history | Open `/api/orders/history` while logged in. | The new order is listed with its status. | BOOK-F-040 to 044 | | |
| U-17 | Buyer | Return request | Open `/api/orders/<order number>/return-refund` and submit the form at the bottom of the page with a reason. | The request is accepted and shows up in `/api/orders/return-refund-requests`. | BOOK-F-040 to 044 | | |
| U-18 | Admin | Ship an order | In `/admin/`, open Orders, select the order and run "Mark selected orders as shipped". | The status becomes SHIPPED. Trying "shipped" again, or cancelling a shipped order, is refused with a warning. | BOOK-F-040 to 044 | | |
| U-19 | Admin | Manage users | Select a test user and run "Deactivate selected users". Try it on your own account too. | The user is deactivated and cannot log in. Your own account is skipped with a warning. | BOOK-F-050 to 054 | | |
| U-20 | Admin | Edit the catalog | In Books, change a price and the stock in the list and save. Run "Mark selected books out of stock" on one book. | The changes show on the site. The out-of-stock book cannot be added to the cart. | BOOK-F-050 to 054 | | |
| U-21 | Seller | Seller scope | Log in to `/admin/` as the seller. Open Books and Orders. Ship one order. Look for a Cancel action. | The seller sees only their own books and the orders that contain them, with the address to ship to. Shipping works. There is no cancel action and no Users section. | BOOK-F-050 to 054, SR-004 | | |
| U-22 | Buyer | Write a review | Open a book page, choose a rating, write a comment and submit. Submit another review for the same book. | The review appears and the average rating updates. The second one is refused. | BOOK-F-060 to 062 | | |
| U-23 | Admin | Moderate a review | In Reviews, select the review and run "Hide selected reviews". Reload the book page. | The review and its rating disappear from the page. | BOOK-F-060 to 062 | | |
| U-24 | Visitor | Admin is protected | Open `/admin/` while logged out and while logged in as a normal buyer. | You are sent to the admin login page both times. | BOOK-SR-004 | | |
| U-25 | Any | Keyboard use | Using only the Tab, Shift+Tab, Enter and Space keys, go from the book list to the cart and through checkout. | Every control can be reached. The focus outline is visible. The "Skip to content" link works. | BOOK-NF-005 | | |
| U-26 | Any | Zoom | Set the browser zoom to 200% on the book list, cart and checkout. | The pages stay usable with no overlapping text. | BOOK-NF-005 | | |

## Results and sign-off

| Total scenarios | Passed | Failed | Not run |
|---|---|---|---|
| 26 |26 |0 |0 |

| Role | Name | Signature / date |
|---|---|---|
| QA Lead | Zia Kadijah | |
| Product Owner | Vidya Sri Ganesh | |