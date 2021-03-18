# Collection Revision
Private revision of a public collection.

After a user has publish a private collection a user can make changes to that collection privately by creating a 
revision. A user must be the owner to revise a public collection.

## Problems to solve
1. Creating a revision from a public collection
1. Modifying resource in the revision
1. Sharing the revision. The resources should be accessable. The public resources should also be accessible and unchanged.
1. Delete resource from the revision does not delete resource from the published collection until published.
1. The user can find the revision.
   
1. publishing the collec
# Solutions
1. Make a complete copy of the existing public collection including copying the dataset and geneset in s3. Allow the 
   to modify this as if it were a private collection. The user can then publish this and it will replace the existing 
   public collection. We can use the `collection_uuid,private` for the revision or add a new type called `revision`. 
   The user can add remove and delete genesets and datasets. The datasets, gene sets and will have different uuids than
   their public counter parts.

1. Add a new column to dataset, geneset, and collection called Shadow_id. This shadow_id would map to the public resource
   of the same type. A user would select revision, and a copy of the collection and all of related rows will be copied 
   with the shadow_id populated with a the uuid of the public resource. The clone will be modified and updated and finally
   published. Publishing will involve replacing the public version with revision by deleting the public version and
   replacing the primary key with the shadow_id.
   

   How do we match up the genesets and datasets when replacing the public dataset?
   What is the difference between a private collection and a revision?
   
