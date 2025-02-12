# scrapes the ap questions from the ebook and stores them in a json file
from ebooklib import epub
from bs4 import BeautifulSoup
import re
import sys
import csv



def scrape(args):

    if len(args) not in [3, 4]:
        print("Usage: python scraper.py scrape <ebook> <q_page> <a_page> [max_n]\nSee avaliable pages with scraper.py list")

    book = epub.read_epub(args[0])

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
    q_page = args[1]
    a_page = args[2]
    # max q to extract (so we don't get frqs)
    max_n = int(args[3]) if len(args) > 3 else None

    # num:[question, answer_choices, correct_answer, explanation, image]
    questions = {}


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
            if max_n and len(questions) >= max_n:
                break
        for p in soup.find_all("p"):
            qs = []
            if re.match("^Questions? [\d+[A-z, ]+refer.*", p.get_text()):
                qs = list(map(lambda x: x[1:], re.findall(" \d+", p.get_text())))
            elif re.match("^Questions? \d+–\d+ refer.+", p.get_text()):
                print(p.get_text())
                qends = re.findall("\d+", p.get_text())
                qs = list(map(str, list(range(int(qends[0]), int(qends[1])+1))))
            else: 
                continue

            # get types of extra info
            ts = re.findall("information|graph|model|chart|diagram|map|table|figure", p.get_text())

            # find the next figure
            if "information" in ts:
                info = p.next_sibling
                for q in qs:
                    questions[q][0] = info.get_text() + "\n" + questions[q][0]
            if "graph" in ts or "map" in ts or "diagram" in ts or "chart" in ts or "figure" in ts:
                figure = p.find_next_sibling(class_="figure")
                if not figure:
                    figure = p.find_next_sibling("div").find(class_="figure")
                img_src = figure.find("img")["src"].split("/")[-1]
                img = book.get_item_with_href(figure.find("img")["src"][3:])
                print(img_src)
                with open("images/"+img_src, "wb") as f:
                    f.write(img.get_content())
                for q in qs:
                    questions[q][-1] = img_src



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
    print("3: ", questions["3"])

    # write to csv file
    with open(metadata[0]+".csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow(["number", "question", "answer_choices", "correct_answer", "explanation", "img_url"])
        for k, v in questions.items():
            writer.writerow([k, v[0], v[1], v[2], v[3], v[4]])

def list_pages(args):
    book = epub.read_epub(args[0])
    for item in book.get_items_of_type(epub.ebooklib.ITEM_DOCUMENT):
        print("--------------------"+item.get_name()+"---------------------")
        soup = BeautifulSoup(item.get_body_content(), "html.parser")
        print(soup.get_text()[0:100])
    return


commands = {"scrape":scrape, "list":list_pages}

def main():
    if len(sys.argv) < 3 or sys.argv[1].lower() not in commands.keys():
        print("Usage: python3 scraper.py <command> <ebook>\nCommands: " + ", ".join(commands.keys()))
        sys.exit(1)

    command = commands[sys.argv[1].lower()]

    command(sys.argv[2:])



if __name__ == "__main__":
    main()

