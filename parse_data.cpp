#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <vector>

#include <boost/algorithm/string/join.hpp>
#include <boost/algorithm/string/predicate.hpp>


using namespace std;

const string ASIN = "ASIN:";
const string GROUP = "group:";
const string ID = "Id:";
const string REVIEW = "reviews:";
const string SALESRANK = "salesrank:";
const string SIMILAR = "similar:";
const string TITLE = "title:";


typedef struct {
    string date;
    int helpful;
    int rating;
    int votes;
    string product_id;
} Review;

typedef struct {
    string asin;
    double avg_rating;
    vector<string>* categories;
    int downloaded_reviews;
    string group;
    int id;
    map<string, Review*>* reviews;
    int salesrank;
    vector<string>* similar;
    string title;
    int total_reviews;
} Product;


void count_user_co_reviews(map<pair<string, string>, int>& co_reviews,
    map<string, Product*>& asin_to_product);
Product* create_product();
Review* create_review();
void make_product_graph(map<string, Product*>& asin_to_product);
void make_user_graph(map<string, int>& user_to_nodeid, map<pair<string, string>, int>& co_reviews);
void parse_file(string filename, map<string, Product*>& asin_to_product,
    map<int, Product*>& id_to_product, map<string, int>& user_to_nodeid);
vector<string> split(string str, char delimiter);


int main()
{
    map<string, Product*> asin_to_product = map<string, Product*>();
    map<int, Product*> id_to_product = map<int, Product*>();
    map<string, int> user_to_nodeid = map<string, int>();
    map<pair<string, string>, int> user_co_reviews = 
        map<pair<string, string>, int>();
    parse_file("amazon-meta.txt", asin_to_product, id_to_product, 
        user_to_nodeid);
    count_user_co_reviews(user_co_reviews, asin_to_product);

    return 0;
}


void count_user_co_reviews(map<pair<string, string>, int>& co_reviews,
    map<string, Product*>& asin_to_product)
{
    int count = 0;
    for (auto it = asin_to_product.begin(); it != asin_to_product.end(); ++it)
    {
        set<string> reviewers;
        for (auto it2 = it->second->reviews->begin(); it2 != it->second->reviews->end(); ++it2)
        {
            reviewers.insert(it2->first);
        }

        for (auto i = reviewers.begin(); i != reviewers.end(); ++i)
        {
            for (auto j = i; ++j != reviewers.end(); )
            {
                co_reviews[pair<string, string>(*i, *j)]++;
            }
        }

        if (++count % 100 == 0)
        {
            cout << count << endl;
        }
    }
}


Product* create_product()
{
    Product* new_product = new Product();
    new_product->categories = new vector<string>();
    new_product->reviews = new map<string, Review*>();
    new_product->similar = new vector<string>();
    return new_product;
}


Review* create_review(string date, string helpful, string rating, string votes,
    string product_id)
{
    Review* new_review = new Review();
    new_review->date = date;
    new_review->helpful = stoi(helpful);
    new_review->rating = stoi(rating);
    new_review->votes = stoi(votes);
    new_review->product_id = product_id;
    return new_review;
}


void parse_file(string filename, map<string, Product*>& asin_to_product,
    map<int, Product*>& id_to_product, map<string, int>& user_to_nodeid)
{
    ifstream infile(filename.c_str());
    cout << "opened" << endl;
    string line;
    Product* current_product = create_product();
    vector<string> tokens;

    int count = 0;
    int user_count = 0;

    while (getline(infile, line))
    {
        if (line.size() <= 1)
        {
            asin_to_product[current_product->asin] = current_product;
            id_to_product[current_product->id] = current_product;
            current_product = create_product();
            count++;
            if (count % 1000 == 0)
            {
                cout << count << endl;
            }
            continue;
        }

        vector<string> tokens = split(line, ' ');

        if (tokens[0].compare(ID) == 0)
        {
            current_product->id = stoi(tokens[1]);
        }
        else if (tokens[0].compare(ASIN) == 0)
        {
            current_product->asin = tokens[1];
        }
        else if (tokens[0].compare(TITLE) == 0)
        {
            tokens.erase(tokens.begin());
            current_product->title = boost::join(tokens, " ");
        }
        else if (tokens[0].compare(GROUP) == 0)
        {
            current_product->group = tokens[1];
        }
        else if (tokens[0].compare(SALESRANK) == 0)
        {
            current_product->salesrank = stoi(tokens[1]);
        }
        else if (tokens[0].compare(SIMILAR) == 0 && stoi(tokens[1]) > 0)
        {
            tokens.erase(tokens.begin(), tokens.begin() + 2);
            for (string& token : tokens)
            {
                current_product->similar->push_back(token);
            }
        }
        else if (boost::starts_with(tokens[0], "|"))
        {
            current_product->categories->push_back(tokens[0]);
        }
        else if (tokens[0].compare(REVIEW) == 0)
        {
            current_product->total_reviews = stoi(tokens[2]);
            current_product->downloaded_reviews = stoi(tokens[4]);
            current_product->avg_rating = stod(tokens[tokens.size() - 1]);
        }
        else if (boost::starts_with(tokens[0], "1") || boost::starts_with(tokens[0], "2"))
        {
            current_product->reviews->insert(pair<string, Review*>(tokens[2],create_review(tokens[0],
                tokens[4], tokens[6], tokens[tokens.size() - 1], 
                current_product->asin)));
            if (user_to_nodeid.find(tokens[2]) == user_to_nodeid.end())
            {
                user_to_nodeid[tokens[2]] = user_count++;
            }
        }
    } 

    infile.close();
}


vector<string> split(string str, char delimiter)
{
    vector<string> tokens;
    stringstream ss(str);
    string token;

    while (getline(ss, token, delimiter))
    {
        if (!token.empty())
        {
            tokens.push_back(token);
        }
    }

    return tokens;
}