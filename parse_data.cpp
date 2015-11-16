#include <ctime>
#include <fstream>
#include <iostream>
#include <list>
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


// review information
typedef struct {
    string date;        // date that the review was created
    int helpful;        // number of people who found the review helpful
    int rating;         // number of stars given to product by this rating (1-5)
    int votes;          // number of people who voted on if the review was helpful
    string product_id;  // product ID
} Review;


// product information
typedef struct {
    string asin;                    // amazon product ID
    double avg_rating;              // average star rating from all of the reviews
    vector<string>* categories;     // categorization of the product
    int downloaded_reviews;         // number of reviews of the product that are captured in the dataset
    string group;                   // major category (books, music, etc.)
    int id;                         // index in the database (probably not useful)
    map<string, Review*>* reviews;  // map of amazon user id -> review struct
    int salesrank;                  // amazon salesrank score
    vector<string>* similar;        // co-purchased product asins
    string title;                   // name of the item
    int total_reviews;              // number of total product reviews, usually equal to downloaded_reviews
} Product;


// function prototypes
void checkBaselinePredictions(set< pair<string, string> >&test_set, map< string, set< string > >&users_to_products, map<string, set< pair<string, double>> >&product_graph);

Product* create_product();
Review* create_review();

void extractTestSet(int num_purchases, vector<string> &user_vector, map< string, set< string > >&users_to_products, set< pair<string, string> >&test_set, map<string, Product*>& asin_to_product);

int getUserEdgeWeight(int user1, int user2);

void group_user_co_reviews(map< pair<int, int>, set<Product*> >& co_reviews, map<string, Product*>& asin_to_product, map<string, int>& user_to_nodeid);

set<string> makeBaselinePrediction(string user, map< string, set< string > >&users_to_products, map<string, set< pair<string, double>> >&product_graph);

void make_product_graph(map<string, Product*> &asin_to_product, map<string, set< pair<string, double>> > &product_graph, map< string, set< string > >&users_to_products);

void make_user_graph(map< string, int>& user_to_nodeid, map<pair<int, int>, set<Product*> >& co_reviews, map< int, set< pair<int, int>> >& user_graph);

void parse_file(string filename, map<string, Product*>& asin_to_product, map<string, int>& user_to_nodeid, map<int, string>& nodeid_to_user, map< string, set< string > > &users_to_products, int &num_purchases, vector<string>&user_vector);

double scoreUsersWhoPurchasedBothProducts(string product1, string product2, map< string, set< string > >&users_to_products, map<string, Product*>& asin_to_product);

vector<string> split(string str, char delimiter);


int main()
{   
    // make sure the random numbers are really random
    // srand(time(NULL))

    /* asin_to_product
        key = (string) amazon product id
        value = (Product*) product object */
    map<string, Product*> asin_to_product = map<string, Product*>();

    /* user_to_nodeid
        key = (string) amazon user id
        value = (int) node id - not sure if this is necessary */
    map<string, int> user_to_nodeid = map<string, int>();

    /* nodeid_to_user
        key = (int) node id
        value = (string) amazon user id */
    map<int, string> nodeid_to_user = map<int, string>();

    /* user_co_reviews
        key = pair (userid1, userid2)
        value = (set) product objects that both users have reviewed */
    map<pair<int, int>, set<Product*> > user_co_reviews = map<pair<int, int>, set<Product*> >();

    /* user_graph
        key = (int) user node
        value = pair (userid2, edge weight) */
    map<int, set< pair<int, int>> > user_graph = map<int, set< pair<int, int>> >();

    /* product_graph
        key = product asin
        value = pair (product asin2, edge weight) */
    map<string, set< pair<string, double>> > product_graph = map<string, set< pair<string, double>> >();

    /* users_to_products
        key = username
        value = set of products user has purchased */
    map< string, set< string > >users_to_products = map< string, set< string > >();

    
    int num_purchases = 0;
    vector<string> user_vector;

    /* parse the data file (makes the product-product graphs), the next two 
     * functions make the user-user graph. using the amazon-small.txt file for 
     * now since the other one is huge. feel free to use the regular datafile. */
    parse_file("amazon-large.txt", asin_to_product, user_to_nodeid, nodeid_to_user, users_to_products, num_purchases, user_vector);

    /* These graphs aren't used to make the baseline predictions so we aren't
     * creating them right now. */
    // group_user_co_reviews(user_co_reviews, asin_to_product, user_to_nodeid);
    // make_user_graph(user_to_nodeid, user_co_reviews, user_graph);

    cout << "asin_to_product: " << asin_to_product.size() << endl;

    // // these two should be the same size
    // cout << "user_to_nodeid: " << user_to_nodeid.size() << endl;
    // cout << "nodeid_to_user: " << nodeid_to_user.size() << endl;

    /* we're not using these one right now */
    // cout << "user_co_reviews: " << user_co_reviews.size() << endl;
    // cout << "user_graph: " << user_graph.size() << endl;

    /* roughly 1/10 purchases will be in the test set. this will allow us to 
     * evaluate the performance of the baseline predictor as well as the one
     * we are creating. the test set items are (string) user id, (string) asin.*/
    cout << "making test set" << endl;
    set< pair<string, string> > test_set = set< pair<string, string> >();
    extractTestSet(num_purchases, user_vector, users_to_products, test_set, asin_to_product);
    cout << "test set size: " << test_set.size() << endl;

    cout << "making product graph" << endl;
    make_product_graph(asin_to_product, product_graph, users_to_products);
    for (auto it = product_graph.begin(); it != product_graph.end(); ++it)
    {
        cout << it->first << endl;
        for (auto it2 = it->second.begin(); it2 != it->second.end(); ++it2)
        {
            cout << '\t' << it2->first << " " << it2->second << endl;
        }
    }

    // cout << "making predictions" << endl;
    // checkBaselinePredictions(test_set, users_to_products, product_graph);

    // cout << "done" << endl;
    return 0;
}


/* Using the product information, create a map of (user ID 1, user ID 2) ->
 * set of Products that they reviewed.
 */
void group_user_co_reviews(map<pair<int, int>, set<Product*> >& co_reviews, map<string, Product*>& asin_to_product, map<string, int>& user_to_nodeid)
{
    int count = 0;

    /* iterate through each product and get the set of users that have written
     * a review for it. then iterate through each pair of users and add that
     * product to their co-reviewed set. */
    for (auto it = asin_to_product.begin(); it != asin_to_product.end(); ++it)
    {
        set<string> reviewers;
        for (auto it2 = it->second->reviews->begin(); it2 != it->second->reviews->end(); ++it2)
        {
            reviewers.insert(it2->first);
        }

        // for each reviewer of this product, add their nodeid's as a pair to co_reviews
        for (auto i = reviewers.begin(); i != reviewers.end(); ++i)
        {
            for (auto j = i; ++j != reviewers.end(); )
            {
                int user1 = user_to_nodeid[*i];
                int user2 = user_to_nodeid[*j];
                co_reviews[pair<int, int>(user1, user2)].insert(it->second);
                co_reviews[pair<int, int>(user2, user1)].insert(it->second);
            }
        }

        if (++count % 100 == 0)
        {
            cout << count << endl;
        }
    }
}


/* Creates and returns a new product struct */
Product* create_product()
{
    Product* new_product = new Product();
    new_product->categories = new vector<string>();
    new_product->reviews = new map<string, Review*>();
    new_product->similar = new vector<string>();
    return new_product;
}


/* Creates and returns a new review struct initialized with the provided
 * information */
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


/* Creates an adjacency list for the graph, node ID -> set of neighboring node
 * IDs. Users that have co-reviewed a product have an edge between them. */
void make_user_graph(map<string, int>& user_to_nodeid, map<pair<int, int>, set<Product*> >& co_reviews, map<int, set< pair<int, int>> >& user_graph)
{
    for (auto it = co_reviews.begin(); it != co_reviews.end(); ++it)
    {
        int user1 = it->first.first;
        int user2 = it->first.second;

        int weight = getUserEdgeWeight(user1, user2);

        user_graph[user1].insert( pair<int, int>(user2, weight) );
        user_graph[user2].insert( pair<int, int>(user1, weight) );
    }
}


int getUserEdgeWeight(int user1, int user2) 
{
    // TODO - FILL IN WHEN IMPLEMENTING OUR ALGORITHM
    return 0;
}


/* Creates the main product-product graph (asin -> product objects; node id ->
 * product object). Also creates the amazon user ID -> node ID graph */
void parse_file(string filename, map<string, Product*>& asin_to_product, map<string, int>& user_to_nodeid, map<int, string>& nodeid_to_user, map< string, set< string > >&users_to_products, int &num_purchases, vector<string>&user_vector)
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

            num_purchases += current_product->total_reviews;
        }
        else if (boost::starts_with(tokens[0], "1") || boost::starts_with(tokens[0], "2"))
        {
            current_product->reviews->insert(pair<string, Review*>(tokens[2],create_review(tokens[0],
                tokens[4], tokens[6], tokens[tokens.size() - 1], 
                current_product->asin)));
            if (user_to_nodeid.find(tokens[2]) == user_to_nodeid.end())
            {
                user_to_nodeid[tokens[2]] = user_count;
                nodeid_to_user[user_count++] = tokens[2];
                users_to_products[tokens[2]] = set< string >();

                user_vector.push_back(tokens[2]);
            }

            // add product to user's set of purchased items
            users_to_products[ tokens[2] ].insert( current_product->asin );
        }
    } 
    asin_to_product[current_product->asin] = current_product;
    current_product = create_product();
    count++;

    infile.close();
}


/* For a given string and delimiter, returns a vector of tokens split using the
 * delimiter. */
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

/*
    Constructs product to product graph
    Weight of edges will be added for baseline */
void make_product_graph(map<string, Product*> &asin_to_product, map<string, set< pair<string, double>> > &product_graph, map< string, set< string > >&users_to_products)
{
    for (auto product_it = asin_to_product.begin(); product_it != asin_to_product.end(); ++product_it)
    {
        string first_product_string = product_it->first;
        Product *first_product = product_it->second;

        for (auto second_product_it = first_product->similar->begin(); second_product_it != first_product->similar->end(); ++second_product_it)
        {
            if (asin_to_product.find(*second_product_it) != asin_to_product.end())
            {
                string second_product_string = *second_product_it;
                Product *second_product = asin_to_product[*second_product_it];

                // number of users that bought object j
                int o_j = second_product->reviews->size();
                double weight;
                if (o_j == 0)
                {
                    weight = 0;
                } else
                {
                    double score = scoreUsersWhoPurchasedBothProducts(first_product_string, second_product_string, users_to_products, asin_to_product);
                    weight = (1.0 / double(o_j)) * score;
                }

                // add edge weight to product graph
                product_graph[ first_product_string ].insert( pair<string, double>(second_product_string, weight) );
            }
        }
    }
}


void printSet(set<string>products)
{
    for (auto it = products.begin(); it != products.end(); ++it)
    {
        cout << *it << ", ";
    }
    cout << endl;
}


double scoreUsersWhoPurchasedBothProducts(string product1, string product2, map< string, set< string > >&users_to_products, map<string, Product*>& asin_to_product)
{
    double sum = 0;
    Product* prod1 = asin_to_product[product1];
    Product* prod2 = asin_to_product[product2];
    for (auto it = prod1->reviews->begin(); it != prod1->reviews->end(); ++it)
    {
        if (prod2->reviews->find(it->first) != prod2->reviews->end())
        {
            sum += 1.0 / double(users_to_products[it->first].size());
        }
    }
    
    return sum;
}


#define PERCENTAGE_TEST_PURCHASES 10
void extractTestSet(int num_purchases, vector<string>& user_vector, map< string, set< string > >& users_to_products, set< pair<string, string> >& test_set, map<string, Product*>& asin_to_product) 
{   
    // int numInTest = int(num_purchases * (PERCENTAGE_TEST_PURCHASES / 100.0));
    int numInTest = 100;
    for (int i = 0; i < numInTest; i++)
    {
        // pick random user that has purchased at least 2 products
        int rand_int = rand() % user_vector.size();
        string chosen_user = user_vector[rand_int];
        bool next = false;
        int tries = 0;
        while ( users_to_products[chosen_user].size() < 2 )
        {
            if (tries++ > 25)
            {
                next = true;
                break;
            }
            rand_int = rand() % user_vector.size();
            chosen_user = user_vector[rand_int];
        }

        if (next || users_to_products[chosen_user].size() == 0)
        {
            i--;
            continue;
        } 

        // now pick random product from user which we will place in the test set
        int rand_product = rand() % users_to_products[chosen_user].size();
        set<string> products = users_to_products[chosen_user];
        string chosen_product;

        int count = 0;
        for (auto product_it = products.begin(); product_it != products.end(); ++product_it)
        {
            chosen_product = *product_it;
            if (count == rand_product) break;
            count++;
        }

        // insert pair into test set and remove from users_to_products
        test_set.insert( pair<string, string>(chosen_user, chosen_product) );
        users_to_products[chosen_user].erase(chosen_product);
        user_vector.erase(remove(user_vector.begin(), user_vector.end(), chosen_user), user_vector.end());
        asin_to_product[chosen_product]->reviews->erase(chosen_user);
    }
}


#define NUMBER_IN_RECOMMENTATION_SET 5

void printRecommendations(vector< pair<string, double> >&productRecommendations)
{
    for (int i = 0; i < NUMBER_IN_RECOMMENTATION_SET; i++)
    {
        if (i < productRecommendations.size())
        {
            cout << (productRecommendations.at(i)).first << ", " << (productRecommendations.at(i)).second << endl;
        }
    }
}


bool sortRecommendationsCmp(const pair<string, double>& edge1, const pair<string, double>& edge2)
{
    return (edge1.second >= edge2.second);
}


set<string> makeBaselinePrediction(string user, map< string, set< string > >& users_to_products, map<string, set< pair<string, double>> >& product_graph)
{
    vector< pair<string, double> >recommendation_candidates = vector<pair<string, double>>();
    
    // iterate over items in user's purchased set
    for (auto items_it = users_to_products[user].begin(); items_it != users_to_products[user].end(); ++items_it)
    {
        string item_asin = *items_it;

        // iterate over edges for a purchased item
        for (auto edges_it = product_graph[item_asin].begin(); edges_it != product_graph[item_asin].end(); ++edges_it)
        {
            pair<string, double>edge = *edges_it;
            recommendation_candidates.push_back(edge);
        }
        // printRecommendations(recommendation_candidates);
    }
    cout << "ended loop" << endl;

    // sort list of recommendations
    sort(recommendation_candidates.begin(), recommendation_candidates.end(), sortRecommendationsCmp);

    cout << "sorted" << endl;

    set<string>productRecommendations = set<string>();
    for (int i = 0; i < NUMBER_IN_RECOMMENTATION_SET; i++)
    {
        if (i >= recommendation_candidates.size()) break;
        productRecommendations.insert((recommendation_candidates.at(i)).first);
    }

    cout << "returning" << endl;
    return productRecommendations;
}


void checkBaselinePredictions(set< pair<string, string> >&test_set, map< string, set< string > >&users_to_products, map<string, set< pair<string, double>> >&product_graph)
{
    int numCorrect = 0;
    for (auto test_it = test_set.begin(); test_it != test_set.end(); ++test_it)
    {
        string user = test_it->first;
        string product = test_it->second;
        cout << user << " " << product << endl;

        set<string>predictions = makeBaselinePrediction(user, users_to_products, product_graph);

        cout << "made baseline prediction" << endl;
        if ( predictions.find(product) != predictions.end() ) numCorrect++;
    }

    cout << "Number of Correct Predictions: " << numCorrect << endl;
    cout << "Percentage Correct: " << 100.0 * (numCorrect / double(test_set.size())) << "%" << endl;
}