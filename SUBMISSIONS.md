# Submit predictions through Hugging Face

Open the [competition Space](https://huggingface.co/spaces/HulaEarth/ai-for-nature-hula-earth) and choose **Submit → Open prediction upload**.

1. Register your team once, including the captain’s Hugging Face username. An organizer approves and links the account.
2. Sign in as that captain. Use **Practice** and the supplied 120-row CSV to check delivery early. Practice produces no model score or final scoring attempt.
3. After test unlock, choose **Final test**, your prediction CSV and the supplied final sample for the local row-ID check. Submit directly. The browser handles encryption and delivery.
4. Keep the receipt and check **Accepted**. Upload received is not yet acceptance.
5. Leave **Make this my final entry if accepted** checked, or use **Use for final** beside an accepted final entry. Check confirmation before **17:30 German time**.

Final CSVs contain exactly 63,590 rows with the header `row_id,score`, every supplied ID once and finite scores in [0,1]. Maximum size: 8 MB. Five accepted final predictions apply per team across the entire event and both delivery routes. Rejections use no accepted attempt and preserve the earlier final choice. Without an explicit choice, the latest accepted final prediction is used.

The original unedited HF server comment binds SHA256 of the exact request manifest, which commits to the ciphertext fingerprint and final-choice instruction. That server timestamp controls eligibility; Git commit dates, browser clocks and later evaluation times do not. Complete the transfer before the deadline and leave time to check acceptance. Keep requests unchanged.

Sessions last one hour. Tokens remain in memory. Pending receipt metadata survives a reload and sign-in, without saving CSVs or tokens. Refresh checks existing results and never resubmits a file. If a transfer is stopped or interrupted, its status is unconfirmed because it may still have reached the provider; check before trying again.

Upload the presentation PDF through the separate Google Form linked below prediction submission. Add a public method/code or checkpoint reference on the upload page and complete the reproducibility report. Do not publish passwords, keys, hidden labels or a raw final CSV.

If a conductor asks you to use backup delivery, open **legacy-submit.html#submit** on the same Space. Its GitHub attachment and nomination forms share the same team quota and final selection. Receipts are labelled `HF-N` and `GH-N` so numbers cannot collide.
