# scrapes the ap questions from the ebook and stores them in a json file
from ebooklib import epub
from bs4 import BeautifulSoup
import re
import sys
import csv

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 scraper.py <ebook>")
        sys.exit(1)

    book = epub.read_epub(sys.argv[1])

    # Extract the metadata from the ebook
    # Title, publisher, author, date, 
    metadata = []
    metadata.append(book.get_metadata("DC", "title")[0][0])
    metadata.append(book.get_metadata("DC", "publisher")[0][0])
    metadata.append(book.get_metadata("DC", "creator")[0][0])
    metadata.append(book.get_metadata("DC", "date")[0][0])
    print(metadata)

    # extract the questions from the ebook

    # page to extract questions from
    q_page = "xhtml/Prin_9780593517147_epub3_p06-c03_r1.xhtml"
    a_page = "xhtml/Prin_9780593517147_epub3_p06-c04_r1.xhtml"
    # max q to extract (so we don't get frqs)
    max_n = 80

    # num:[question, answer_choices, correct_answer, explanation]
    questions = {}

    # for item in book.get_items_of_type(epub.ebooklib.ITEM_DOCUMENT):
    #     print(item.get_name())
    #     soup = BeautifulSoup(item.get_body_content(), "html.parser")
    #     print(soup.get_text()[0:100])
    # return

    # works for princeton
    for item in book.get_items_of_type(epub.ebooklib.ITEM_DOCUMENT):
        if item.get_name() != q_page:
            continue
        soup = BeautifulSoup(item.get_body_content(), "html.parser")
        for div in soup.find_all("div"):
            p = div.find("p")
            if not p: continue
            m = re.match("^\d+.", p.get_text())
            if not m:
                continue
            question = [p.get_text()[len(m.group()):].strip(), ""]
            for p in div.find_all("p")[1:]:
                question[1] += p.get_text() + "\n"
            questions[m.group()[:-1]] = question
            if len(questions) >= max_n:
                break
    for item in book.get_items_of_type(epub.ebooklib.ITEM_DOCUMENT):
        if item.get_name() != a_page:
            continue
        soup = BeautifulSoup(item.get_body_content(), "html.parser")
        for div in soup.find_all("div"):
            p = div.find("p")
            if not p: continue
            m = re.match("^\d+.", p.get_text())
            if not m:
                continue
            num = m.group()[:-1]
            if len(questions[num]) > 2:
                continue
            ans = p.get_text().split(" ")[-1]
            explanation = ""
            for p in div.find_all("p")[1:2]:
                explanation += p.get_text() + "\n"
            questions[num].append(ans)
            questions[num].append(explanation)

        


    # print(questions)
    print(questions["1"])

    # write to csv file
    # with open(metadata[0]+".csv", "w") as f:
    #     writer = csv.writer(f)
    #     writer.writerow(["Number", "Question", "Answer Choices", "Correct Answer", "Explanation"])
    #     for k, v in questions.items():
    #         writer.writerow([k, v[0], v[1], v[2], v[3]])



if __name__ == "__main__":
    main()

