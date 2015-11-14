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


// review information
typedef struct {
    string date;
    int helpful;
    int rating;
    int votes;
    string product_id;
} Review;


// product information
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


// function prototypes
void group_user_co_reviews(map< pair<int, int>, set<Product*> >& co_reviews, map<string, Product*>& asin_to_product, map<string, int>& user_to_nodeid);
Product* create_product();
Review* create_review();
void make_product_graph(map<string, Product*>& asin_to_product);
void make_user_graph(map< string, int>& user_to_nodeid, map<pair<int, int>, set<Product*> >& co_reviews, map< int, set< pair<int, int>> >& user_graph);
// void parse_file(string filename, map<string, Product*>& asin_to_product, map<int, Product*>& id_to_product, map<string, int>& user_to_nodeid, map<int, string>& nodeid_to_user);
void parse_file(string filename, map<string, Product*>& asin_to_product, map<int, Product*>& id_to_product, map<string, int>& user_to_nodeid, map<int, string>& nodeid_to_user, map< string, set< string > > &users_to_products);
vector<string> split(string str, char delimiter);

int getUserEdgeWeight(int user1, int user2);
void make_product_graph(map<string, Product*> &asin_to_product, map<string, set< pair<string, double>> > &product_graph, map< string, set< string > >users_to_products);

double scoreUsersWhoPurchasedBothProducts(string product1, string product2, map< string, set< string > >users_to_products);


int main()
{
    // initialize the maps/graphs
    map<string, Product*> asin_to_product = map<string, Product*>();
    map<int, Product*> id_to_product = map<int, Product*>();
    map<string, int> user_to_nodeid = map<string, int>();
    map<int, string> nodeid_to_user = map<int, string>();
    map<pair<int, int>, set<Product*> > user_co_reviews = 
        map<pair<int, int>, set<Product*> >();

    /*
    user_graph
        key = user node
        value = pair (userid2, edge weight)
    */
    map<int, set< pair<int, int>> > user_graph = map<int, set< pair<int, int>> >();

    /*
    product_graph
        key = product asin
        value = pair (product asin2, edge weight)
    */
    map<string, set< pair<string, double>> > product_graph = map<string, set< pair<string, double>> >();

    /*
    users_to_products
        key = username
        value = set of products user has purchased
    */
    map< string, set< string > >users_to_products = map< string, set< string > >();

    
    // parse the data file (makes the product-product graphs), the next two 
    // functions make the user-user graph. using the amazon-small.txt file for 
    // now since the other one is huge. feel free to use the regular data file.
    parse_file("test.txt", asin_to_product, id_to_product, user_to_nodeid, nodeid_to_user, users_to_products);
    // parse_file("amazon-small.txt", asin_to_product, id_to_product, user_to_nodeid, nodeid_to_user);

    group_user_co_reviews(user_co_reviews, asin_to_product, user_to_nodeid);
    make_user_graph(user_to_nodeid, user_co_reviews, user_graph);

    // these two should be the same size
    cout << "asin_to_product: " << asin_to_product.size() << endl;
    cout << "id_to_product: " << id_to_product.size() << endl;

    // these two should be the same size
    cout << "user_to_nodeid: " << user_to_nodeid.size() << endl;
    cout << "nodeid_to_user: " << nodeid_to_user.size() << endl;

    // 25,000 users create 13 million co-reviews, this is huge
    cout << "user_co_reviews: " << user_co_reviews.size() << endl;

    /* this doesn't equal the size of the user_to_nodeid or node_id_to_user 
     * graphs because some users don't have neighbors. however, it looks like
     * there are only 300/25000 users that fall into this category.
     */
    cout << "user_graph: " << user_graph.size() << endl;


    make_product_graph(asin_to_product, product_graph, users_to_products);


    return 0;
}


/* Using the product information, create a map of (user ID 1, user ID 2) ->
 * set of Products that they reviewed.
 */
void group_user_co_reviews(map<pair<int, int>, set<Product*> >& co_reviews, map<string, Product*>& asin_to_product, map<string, int>& user_to_nodeid)
{
    // int count = 0;
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

        // if (++count % 100 == 0)
        // {
        //     cout << count << endl;
        // }
    }
}


/* Creates and returns a new product struct
 */
Product* create_product()
{
    Product* new_product = new Product();
    new_product->categories = new vector<string>();
    new_product->reviews = new map<string, Review*>();
    new_product->similar = new vector<string>();
    return new_product;
}


/* Creates and returns a new review struct initialized with the provided
 * information
 */
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
 * IDs.
 */
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


int getUserEdgeWeight(int user1, int user2){
    // TODO - FILL IN WHEN IMPLEMENTING OUR ALGORITHM
    return 0;
}




/* Creates the main product-product graph (asin -> product objects; node id ->
 * product object). Also creates the amazon user ID -> node ID graph
 */
// void parse_file(string filename, map<string, Product*>& asin_to_product, map<int, Product*>& id_to_product, map<string, int>& user_to_nodeid, map<int, string>& nodeid_to_user, map< string)
void parse_file(string filename, map<string, Product*>& asin_to_product, map<int, Product*>& id_to_product, map<string, int>& user_to_nodeid, map<int, string>& nodeid_to_user, map< string, set< string > >&users_to_products)
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
            if (count == 10) break;
            // if (count % 1000 == 0)
            // {
            //     cout << count << endl;
            // }
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
                user_to_nodeid[tokens[2]] = user_count;
                nodeid_to_user[user_count++] = tokens[2];
                users_to_products[tokens[2]] = set< string >();
            }

            // add product to user's set of purchased items
            users_to_products[ tokens[2] ].insert( current_product->asin );
        }
    } 
    asin_to_product[current_product->asin] = current_product;
    id_to_product[current_product->id] = current_product;
    current_product = create_product();
    count++;

    infile.close();
}


/* For a given string and delimiter, returns a vector of tokens split using the
 * delimiter.
 */
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
    Weight of edges will be added for baseline
*/
void make_product_graph(map<string, Product*> &asin_to_product, map<string, set< pair<string, double>> > &product_graph, map< string, set< string > >users_to_products){

    for (auto product_it = asin_to_product.begin(); product_it != asin_to_product.end(); ++product_it){

        string firstProductString = product_it->first;
        Product *firstProduct = product_it->second;

        for (auto second_product_it = firstProduct->similar->begin(); second_product_it != firstProduct->similar->end(); ++second_product_it){

            string secondProductString = *second_product_it;
            Product *secondProduct = asin_to_product[*second_product_it];

            // number of users that bought object j
            int o_j = secondProduct->reviews->size();

            double score = scoreUsersWhoPurchasedBothProducts(firstProductString, secondProductString, users_to_products);

            double weight = (1/double(o_j))*score;
            // cout << firstProductString << ", " << secondProductString << " - " << score << endl;
            // add edge weight to product graph
            product_graph[ firstProductString ].insert( pair<string, double>(secondProductString, weight) );
        }
    }
}


void printSet(set<string>products){
    for (auto it = products.begin(); it != products.end(); ++it){
        cout << *it << ", ";
    }
    cout << endl;
}


double scoreUsersWhoPurchasedBothProducts(string product1, string product2, map< string, set< string > >users_to_products){

    double sum = 0;
    // cout << users_to_products.size() << endl;
    
    for (auto user_it = users_to_products.begin(); user_it != users_to_products.end(); ++user_it){
        // string user = user_it->first;
        // cout << user_it->first << ": ";
        set<string>products = user_it->second;
        // printSet(products);

        int userHasBoth = 0;
        if(products.find(product1) != products.end() && products.find(product2) != products.end()) userHasBoth = 1;

        int u_l = products.size();

        sum += userHasBoth/double(u_l);
    }
    return sum;
}









