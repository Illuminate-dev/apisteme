UPDATE questions SET image_url = newtable.img_url FROM newtable WHERE questions.explanation = newtable.explanation;
UPDATE questions SET question = newtable.question FROM newtable WHERE questions.explanation = newtable.explanation;
