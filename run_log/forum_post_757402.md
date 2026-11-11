# Forum post 757402: public time-stamp of prereg-v1.0

- URL: https://www.kaggle.com/competitions/gemma-4-developer-agent-paper/discussion/757402
- Title: Pre-registration hash
- Author shown: raikhan
- Post time: Mon Nov 09 2026 12:00:14 GMT-0600 (Central Standard Time) = 2026-11-09T18:00:14Z. Source: the title attribute of the page's "3 minutes ago" element.
- Time read: 2026-11-09T18:03:32Z (browser clock at reading).
- How read: built-in browser, signed out (the page showed Login and Sign Up). Plain curl returned only the page shell, with no post text.
- Comments at reading: 0.
- Hash in the post (only 64-hex string on the page): c4d82769f7607766066ffa8986dd16576499dc7b835cf3d94b8f9a9766be5ced
- Expected hash: c4d82769f7607766066ffa8986dd16576499dc7b835cf3d94b8f9a9766be5ced
- Exact string comparison in the page: equal.

## Full post text

prereg-v1.0 SHA-256: c4d82769f7607766066ffa8986dd16576499dc7b835cf3d94b8f9a9766be5ced

Time-stamp of a pre-registered analysis plan. The hashed files will be released with our writeup, with a script that recomputes this hash.

## Local check of the snapshot

- frozen/prereg-v1.0.tar.gz SHA-256: 42593ad7a80c89496a9117d679a480a7b90d21ffe7302e37243247397cacb2ce (matches expected).
- Unpacked to studyA-v1.0/. `python -m ngraph.commit verify` on prereg/MANIFEST_prereg-v1.0.txt: ok true, 181 files, no mismatched, missing or unlisted files, manifest_sha256 equals the posted hash.

# Reply: public time-stamp of prereg-v1.1 (Study B addendum)

- URL: https://www.kaggle.com/competitions/gemma-4-developer-agent-paper/discussion/757402#3552845 (comment id 3552845 in the topic above)
- Author shown: raikhan (Topic Author)
- Reply time: Tue Nov 10 2026 06:38:04 GMT-0600 (Central Standard Time) = 2026-11-10T12:38:04Z. Source: the title attribute of the reply's "4 minutes ago" element.
- Time read: 2026-11-10T12:42:11Z (browser clock at reading).
- How read: built-in browser, signed out (the page showed "Please sign in to reply to this topic"). The topic URL without the comment anchor first showed "0 Comments" twice (12:41:25Z and, after a reload, 12:41:42Z); the topic list showed the comment, and the URL with the anchor `#3552845` showed "1 Comment".
- Comments at reading: 1.
- 64-hex strings on the page, copied from the page text: c4d82769f7607766066ffa8986dd16576499dc7b835cf3d94b8f9a9766be5ced (first post) and 86312d42c3cda411e851bdfbfa5a595d4f9bc35334e595167ead0bff3c4afa4c (reply).
- First post unchanged: its text and its time (2026-11-09T18:00:14Z) read as before; its hash equals the `follows` hash in prereg/MANIFEST_prereg-v1.1.txt (`# follows: prereg-v1.0 c4d82769f7607766066ffa8986dd16576499dc7b835cf3d94b8f9a9766be5ced`).

## Full reply text

prereg-v1.1 (addendum) SHA-256: 86312d42c3cda411e851bdfbfa5a595d4f9bc35334e595167ead0bff3c4afa4c

(The page renders the reply's two lines as one line of text.)

## Local check

`python -m ngraph.commit verify --manifest prereg/MANIFEST_prereg-v1.1.txt --expect 86312d42c3cda411e851bdfbfa5a595d4f9bc35334e595167ead0bff3c4afa4c`, run in the package at about 12:43Z: exit 0; ok true; matches_expected true; 188 files; no mismatched, missing or unlisted files; chain_ok true; follows prereg-v1.0 c4d82769f7607766066ffa8986dd16576499dc7b835cf3d94b8f9a9766be5ced. Full output: gemma4-staging/addendum11/verify_expect.txt.

- frozen/prereg-v1.1.tar.gz SHA-256: 50276e3e5c81a61bc8f7924fce489ffdc6e5226e6b62c29858ad26b83b21d927, 9,466,970 bytes (189 files).
