"""
sample program to extract bible passage given reference
reference supplied in the form:
- 
"""
import re
import string

# constants
FILE_PATH = 'bible.txt'

def retrieveBible():
    bible = {}
    books = []
    chars_to_remove = string.punctuation + string.digits

    try:
        with open(FILE_PATH, mode='r', newline='', encoding='utf-8') as file:
            # Skip first 3 lines
            next(file) 
            next(file)
            next(file)
        
            for line in file:
                # format: <reference> <content> (space here is a tab char)
                # thus tab becomes delimiter for separation
                k, v = line.strip('\n').split('\t', 1)
                bible[k] = v

                book = k.rstrip(chars_to_remove).strip()
                if book not in books:
                    books.append(book)
                
        return bible, books

    except FileNotFoundError:
        print(f"Error: The file '{FILE_PATH}' was not found.")
        return {}, []


def getNumVerses(bible, book, chapter):
    return len([k for k in bible.keys() if k.startswith(f"{book} {chapter}:")])


def printPassage(book, startChapter, startVerse, endChapter, endVerse):
    """
    Prints the passage given as args in one of the following forms:
    Genesis 1:1
    Genesis 1:1-31
    Genesis 1:1-2:3
    1 Corinthians 15:51
    """
    if (startChapter == endChapter and startVerse == endVerse):
        return f"{book} {startChapter}:{startVerse}"

    elif (startChapter == endChapter):
        return f"{book} {startChapter}:{startVerse}-{endVerse}"

    else:
        return f"{book} {startChapter}:{startVerse}-{endChapter}:{endVerse}"


def extractPassage(book, startChapter, startVerse, endChapter, endVerse):
    """
    Reference supplied as separate arguments listed below. Assume same book.
    Extracts between startChapter and endChapter INCLUSIVE, and startVerse and endVerse INCLUSIVE
    
    :param book: Book of the bible
    :param startChapter: Chapter to start from
    :param startVerse: Verse to start from
    :param endChapter: Chapter to end at. Can be same as startChapter
    :param endVerse: Verse to end at. Can be same as startVerse

    Return the passage as a string
    Throws an error if the passage does not exist or is out of bounds
    """

    bible, books = retrieveBible()

    # error checking
    if book not in books:
        raise ValueError("book does not exist in the bible")
    if (endChapter < startChapter):
        raise ValueError("endChapter must be greater or equal to startChapter")
    if (endChapter == startChapter and endVerse < startVerse):
        raise ValueError("endVerse must be greater or equal to startVerse")
    
    content = ""

    # put arguments into form <Book> <Chapter>:<Verse>
    if (startChapter == endChapter and startVerse == endVerse):
        # only 1 verse to retrieve
        reference = f"{book} {startChapter}:{startVerse}"
        # print(reference)
        try:
            return bible[reference]
        except KeyError:
            raise IndexError("Chapter and/or verse do not exist or are out of bounds")

    elif (startChapter == endChapter):
        # only retrieve within same chapter

        # error checking
        startRef = f"{book} {startChapter}:{startVerse}"
        endRef = f"{book} {startChapter}:{endVerse}"
        try:
            bible[startRef]
            bible[endRef]
        except KeyError:
            raise IndexError("Chapter and/or verses do not exist or are out of bounds")

        # retireve contents of reference
        for i in range(endVerse - startVerse + 1):
            reference = f"{book} {startChapter}:{startVerse + i}"
            # print(reference)
            content += bible[reference] + " "

        return content

    else:
        # most complex case
        # chapter 1: startVerse to verse m, last verse in that chapter
        # chapter 2-(n-1): all verses
        # chapter n: verse 1 to endVerse

        # error checking
        startRef = f"{book} {startChapter}:{startVerse}"
        endRef = f"{book} {startChapter}:{endVerse}"
        try:
            bible[startRef]
            bible[endRef]
        except KeyError:
            raise IndexError("Chapter and/or verses do not exist or are out of bounds")

        # get verses in startChapter from startVerse to end of chapter
        for i in range(getNumVerses(bible, book, startChapter) - startVerse):
            reference = f"{book} {startChapter}:{startVerse + i}"
            # print(reference)
            content += bible[reference] + " "

        # get all verses in any chapters between the start and end chapter
        for i in range((endChapter - 1) - (startChapter + 1) + 1):
            newChapter = startChapter + 1 + i
            for j in range(getNumVerses(bible, book, newChapter)):
                reference = f"{book} {newChapter}:{j + 1}"
                # print(reference)
                content += bible[reference] + " "

        # get verses in endChapter from start of chapter to endVerse
        for i in range(endVerse):
            reference = f"{book} {endChapter}:{i + 1}"
            # print(reference)
            content += bible[reference] + " "

        return content


def extractReference(reference):
    """
    Reference supplied as a single string argument in the following form:
    
    :param reference: <book> <chapter>:<verse>-<chapter>:<verse>
    Alternatively for same chapters: <book> <chapter>:<verse>-<verse>

    This function needs to handle all of the above cases.
    - Genesis 1:1
    - Genesis 1:1-31
    - Genesis 1:1-2:3
    - 1 Samuel 2:20-24

    Return the passage as a string
    Throws an error if the passage does not exist or is out of bounds
    """
    pass


def main():
    print("SelahSearch Extraction: Get your bible passage here!")
    book = input("Enter book: ")
    startChapter = int(input("Enter chapter to start from: "))
    startVerse = int(input("Enter verse to start from: "))
    endChapter = int(input("Enter chapter to end at: "))
    endVerse = int(input("Enter verse to end at: "))
    
    print(f"\nRetrieving the contents of {printPassage(book, startChapter, startVerse, endChapter, endVerse)}\n")
    print(extractPassage(book, startChapter, startVerse, endChapter, endVerse))
    print()


if __name__ == "__main__":
    main()
