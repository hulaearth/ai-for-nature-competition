# Team registration and prediction uploads

Use the competition Space's **Submit** page. Train and run inference on your own compute; upload predictions, not executable model artifacts.

## Register

Create a [team registration issue](https://github.com/hulaearth/ai-for-nature-competition/issues/new?template=register-team.yml) from the designated uploader's account. List a team name and the public GitHub usernames of all two or three members. The organizer approves the team and assigns its slug. One account uploads and nominates for the team; do not share account credentials.

Before kickoff, use only download, unpacking, checksum and environment checks; challenge-data analysis, model fitting and visual insights start at kickoff. The supplied neutral practice CSV can be used to check delivery without fitting a model.

## Practice before final-test release

Use the [120-row practice CSV](site/practice_submission.csv). On the Space, select the approved team and “Practice format check”, select the CSV and click **Check and encrypt locally**, then download the encrypted JSON. Attach the resulting `.encrypted.json` to a Practice issue and create the issue. This checks encryption, keys, format and delivery; it awards no model score and consumes no final-test attempt.

## Final-test CSV

At the announced test release, use the starter's unlock helper on locally cached encrypted files. Generate one score for every row of the decrypted sample submission:

```csv
row_id,score
0123456789abcdef0123456789abcdef,0.42
```

The example ID above is illustrative. Use the **exact 63,590 keys from the competition sample**, without duplicates or extras. Order does not matter. Scores must be finite numbers between 0 and 1. Raw CSV size is limited to 8 MB. Do not include species, coordinates, indexes, explanations or other columns.

Encrypt on the Space using the approved team and “Final-test prediction”. Download the encrypted JSON, open the matching GitHub issue form, attach the file and wait for the attachment link to finish appearing. Create the issue before the deadline. **Downloading the encrypted file alone is not a submission.** Keep the issue URL and do not edit the issue. Corrections use a new issue.

There are five accepted final-test submissions per team over the entire event. Invalid files do not consume an accepted attempt; twenty invalid requests per team/channel trigger a safety limit. Reordered identical predictions are not a new attempt. Public attachment content is encrypted; never attach a raw CSV or upload one through a PR.

## Feedback and your final choice

The private worker checks the approved uploader's numeric GitHub ID, original issue receipt time, edit status, encryption, complete keys and quota. It saves the accepted file and receipt privately before publishing status. Feedback is queued and can take several minutes; GitHub's original issue timestamp determines whether a timely valid upload met the deadline.

The provisional board displays aggregate public pooled-country species macro average precision. Higher is better. Missing underlying labels remain unscored. No private scores or species/country details are returned during the event.

Your **latest accepted prediction** is the default final file; it is not automatically the highest public AP. To choose an older accepted file, use [Choose / confirm final entry](https://github.com/hulaearth/ai-for-nature-competition/issues/new?template=nomination.yml) before 17:30 and enter its Prediction issue number. This form selects a file already uploaded; do not upload predictions again. The latest valid explicit choice overrides the default. Use it to confirm your method/code and presentation references too.

For example: #12 is accepted, then #16 is accepted. With no explicit choice, #16 is final. Choose #12 in the form and #12 is final instead. A rejected later upload does not replace an accepted file. The private split is scored only after all timely requests are reconciled and selections sealed.

Share your code/checkpoint reference and method report by the work deadline. Upload the final presentation PDF through the announced presentation form: one PDF up to 10 MB is required, and one presentation source file up to 100 MB is optional. The latest complete valid response before the deadline is used. Identify the form submission in the nomination; the slides remain in private organizer storage. Record the original CSV SHA256 shown in the receipt. Report the common German development result and any final train-plus-development refit. The complete permitted-data and validation rules are on the Space's Rules page.

See the [participant PDF, released at 10:00](https://huggingface.co/spaces/Hula-Tech/ai-for-nature-hula-earth), [practical workflow and FAQ](site/guide.html), and [Challenge data](https://drive.google.com/drive/folders/1gXsJyZnI8QIbk1RQYL0qNqy1yf0eSaoT). The Google Drive folder name is Challenge data; the frozen dataset remains bird-habitat-2024.
