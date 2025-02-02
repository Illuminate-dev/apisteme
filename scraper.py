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
    q_page = "xhtml/Prin_9780593517147_epub3_p02-c01_r1.xhtml"
    a_page = "xhtml/Prin_9780593517147_epub3_p02-c02_r1.xhtml"
    # max q to extract (so we don't get frqs)
    max_n = 80

    # num:[question, answer_choices, correct_answer, explanation, image]
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

            figure = div.find(class_="figure")
            img_src = ""
            if figure:
                img_src = figure.find("img")["src"].split("/")[-1]
                img = book.get_item_with_href(figure.find("img")["src"][3:])
                print(img_src)
                with open("images/"+img_src, "wb") as f:
                    f.write(img.get_content())
            
            question = [p.get_text()[len(m.group()):].strip(), "", "", "", img_src]
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
            if questions[num][2] != "":
                continue
            ans = p.get_text().split(" ")[-1]
            explanation = ""
            for p in div.find_all("p")[1:2]:
                explanation += p.get_text() + "\n"
            questions[num][2] = ans
            questions[num][3] = explanation

        


    # print(questions)
    print(questions["5"])

    # write to csv file
    # with open(metadata[0]+".csv", "w") as f:
    #     writer = csv.writer(f)
    #     writer.writerow(["number", "question", "answer_choices", "correct_answer", "explanation", "img_url"])
    #     for k, v in questions.items():
    #         writer.writerow([k, v[0], v[1], v[2], v[3], v[4]])



if __name__ == "__main__":
    main()

