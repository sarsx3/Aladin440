# Movie Playlist Fixer

সোর্স প্লেলিস্ট:
`https://raw.githubusercontent.com/sm-monirulislam/SM-Movie-Hup-Auto-Update/refs/heads/main/Movie_Combined.m3u`

এই রিপোটা প্রতি ১৫ মিনিট পরপর ওই সোর্স প্লেলিস্ট ফেচ করে, প্রতিটা স্ট্রিম এন্ট্রির
`#EXTVLCOPT:http-referrer` (আর থাকলে `http-user-agent`) ঠিকভাবে বসিয়ে
`docs/Movie_Combined_Fixed.m3u` নামে একটা "ফিক্সড" প্লেলিস্ট জেনারেট করে repo-তে
commit করে দেয়।

## কীভাবে সেটআপ করবে

1. **নতুন একটা GitHub repo বানাও** (public হলে সবচেয়ে সহজ — তাহলে raw link সরাসরি কাজ করবে)।
2. এই ফোল্ডারের সবকিছু (`.github/`, `scripts/`, `docs/`, `README.md`) repo-তে push করো।
3. Repo-র **Settings → Actions → General → Workflow permissions**-এ গিয়ে
   **"Read and write permissions"** সিলেক্ট করে সেভ করো।
   (এটা না করলে Action commit/push করতে পারবে না।)
4. **Actions** ট্যাবে গিয়ে "Fix Movie Playlist" workflow-টা একবার ম্যানুয়ালি
   **Run workflow** দিয়ে চালিয়ে দেখো — `docs/Movie_Combined_Fixed.m3u` ফাইলটা
   তৈরি হয়ে commit হয়ে যাবে।
5. এরপর থেকে এটা প্রতি ১৫ মিনিটে নিজে থেকেই চলবে এবং আপডেট থাকবে।

## তোমার অ্যাপে কোন URL ব্যবহার করবে

```
https://raw.githubusercontent.com/<তোমার-ইউজারনেম>/<repo-নাম>/main/docs/Movie_Combined_Fixed.m3u
```

এই URL-টাই তোমার অ্যাপের প্লেলিস্ট সোর্স হিসেবে বসিয়ে দাও (আগের সোর্স URL-এর বদলে)।

## স্ক্রিপ্ট কীভাবে কাজ করে (সংক্ষেপে)

- সোর্স প্লেলিস্টের যেসব এন্ট্রিতে ইতিমধ্যে সঠিক `http-referrer` ট্যাগ আছে, সেখান
  থেকে প্রতিটা ডোমেইনের জন্য সবচেয়ে বেশি ব্যবহৃত (majority) মান শেখে।
- যেসব এন্ট্রিতে এই ট্যাগ নেই কিন্তু ডোমেইনটা চেনা, সেখানে শেখা মানটা বসিয়ে দেয়।
- এভাবে ডোমেইন/Referer হার্ডকোড না করেই কাজ করে — সোর্স নতুন ডোমেইন বা নতুন
  Referer যোগ করলেও (যদি অন্তত একটা উদাহরণ ট্যাগসহ থাকে) স্ক্রিপ্ট নিজে থেকেই
  শিখে নেবে।
- Run log-এ কোনো ডোমেইন "unknown" থাকলে (কোনো উদাহরণ না থাকায় শেখা যায়নি) সেটা
  warning হিসেবে দেখাবে — চাইলে পরে ম্যানুয়ালি স্ক্রিপ্টে default referrer যোগ করা
  যাবে।

## শিডিউল বদলানো

`.github/workflows/fix-playlist.yml` ফাইলে `cron: "*/15 * * * *"` লাইনটা বদলে
তুমি চাইলে কম/বেশি ঘন ঘন চালাতে পারো (তবে GitHub Actions free tier-এ খুব ঘন ঘন
(যেমন প্রতি মিনিটে) শিডিউল চালালে minute limit শেষ হয়ে যেতে পারে — ১৫ মিনিট একটা
ভালো ব্যালেন্স)।
